from __future__ import annotations

from backend.core.preprocessor import (
    chunk_paragraphs,
    detect_key_points,
    detect_language,
    evaluate_yaml_quality,
    extract_named_entities,
    parse_chapters,
)

SAMPLE_CN = """第一章 启程
少年林风站在村口的古树下，目光望向远方的山脉。他从小就知道，自己不属于这里。
"我必须走。"他握紧了手中的戒指。

第二章 遇险
山路比想象中更加艰险。林风遇到了第一只妖兽，那是一只浑身漆黑的巨狼。
他拔出父亲留下的剑，手在颤抖。

第三章 盟友
就在林风快要支撑不住时，一道白色的身影从树林中窜出。
"需要帮忙吗？"精灵公主艾琳微笑着问道。"""

SAMPLE_EN = """Chapter 1: The Beginning
John stood at the edge of the cliff, watching the sunrise. Today would change everything.

Chapter 2: The Encounter
The forest was darker than John had imagined. A shadow moved between the trees.
"Who's there?" he called out.

Chapter 3: The Alliance
A figure emerged from the darkness. It was Sarah, the rogue agent he'd been tracking.
"We have the same enemy," she said. "We should work together." """


class TestParseChapters:
    def test_detects_chinese_chapter_pattern(self) -> None:
        chapters = parse_chapters(SAMPLE_CN)
        assert len(chapters) >= 3
        assert any("启程" in c["title"] for c in chapters)

    def test_detects_english_chapter_pattern(self) -> None:
        chapters = parse_chapters(SAMPLE_EN)
        assert len(chapters) >= 3
        assert any("Beginning" in c["title"] for c in chapters)

    def test_returns_one_chapter_when_no_markers(self) -> None:
        chapters = parse_chapters("This is just a simple paragraph with no chapter markers at all.")
        assert len(chapters) == 1
        assert chapters[0]["title"] == "全文"


class TestChunkParagraphs:
    def test_splits_by_paragraph_and_groups_by_max_chars(self) -> None:
        text = "Short para 1.\n\nShort para 2.\n\nShort para 3."
        chunks = chunk_paragraphs(text, max_chars=15)
        assert len(chunks) >= 1
        assert all(len(c["text"]) <= 40 for c in chunks)

    def test_returns_list_of_dicts_with_text_and_source_keys(self) -> None:
        text = "Paragraph one.\n\nParagraph two."
        chunks = chunk_paragraphs(text, max_chars=500)
        assert isinstance(chunks, list)
        for c in chunks:
            assert "text" in c
            assert "source" in c
            assert c["source"].startswith("chunk_")


class TestDetectLanguage:
    def test_returns_chinese_for_chinese_text(self) -> None:
        result = detect_language("少年林风站在村口的古树下，目光望向远方的山脉。")
        assert result == "chinese"

    def test_returns_english_for_english_text(self) -> None:
        result = detect_language("John stood at the edge of the cliff, watching the sunrise.")
        assert result == "english"


class TestExtractNamedEntities:
    def test_returns_dict_with_characters_and_locations_keys(self) -> None:
        result = extract_named_entities(SAMPLE_CN)
        assert isinstance(result, dict)
        assert "characters" in result
        assert "locations" in result


class TestDetectKeyPoints:
    def test_extracts_dialogues_from_chinese_text(self) -> None:
        result = detect_key_points(SAMPLE_CN)
        assert len(result["dialogues"]) >= 2
        assert any("我必须走" in d for d in result["dialogues"])

    def test_extracts_dialogues_from_english_text(self) -> None:
        result = detect_key_points(SAMPLE_EN)
        assert len(result["dialogues"]) >= 2
        assert any("Who's there" in d for d in result["dialogues"])

    def test_returns_first_and_last_chars(self) -> None:
        result = detect_key_points(SAMPLE_CN)
        assert len(result["first_chars"]) > 0
        assert len(result["last_chars"]) > 0
        assert "少年林风" in result["first_chars"]

    def test_returns_ending_sentences(self) -> None:
        result = detect_key_points(SAMPLE_CN)
        assert len(result["ending_sentences"]) >= 1

    def test_returns_must_preserve_string(self) -> None:
        result = detect_key_points(SAMPLE_CN)
        assert len(result["must_preserve"]) > 50
        assert "文本开头" in result["must_preserve"]
        assert "文本结尾" in result["must_preserve"]

    def test_returns_time_location_pairs(self) -> None:
        result = detect_key_points(SAMPLE_CN)
        assert isinstance(result["time_location_pairs"], list)


class TestEvaluateYamlQuality:
    def test_detects_valid_yaml(self) -> None:
        yaml_str = """
episodes:
- scenes:
  - beats:
    - type: dialogue
      character_id: char_001
      content: Hello
      emotion: joy
    duration_estimate: 60s
  - beats:
    - type: action
      content: walks
      emotion: tension
    duration_estimate: 120s
"""
        result = evaluate_yaml_quality(yaml_str)
        assert result["valid_yaml"] is True
        assert result["beat_count"] >= 2

    def test_detects_missing_emotions(self) -> None:
        yaml_str = """
episodes:
- scenes:
  - beats:
    - type: action
      content: test
      emotion: null
    duration_estimate: 60s
"""
        result = evaluate_yaml_quality(yaml_str)
        assert result["emotion_null_rate"] > 0.8
        assert any("Emotion missing" in i for i in result["issues"])

    def test_detects_missing_character_ids(self) -> None:
        yaml_str = """
episodes:
- scenes:
  - beats:
    - type: dialogue
      character_id: null
      content: test
      emotion: fear
    - type: dialogue
      character_id: char_001
      content: test2
      emotion: anger
    duration_estimate: 60s
"""
        result = evaluate_yaml_quality(yaml_str)
        assert result["char_id_null_rate"] >= 0.4

    def test_detects_low_duration_diversity(self) -> None:
        yaml_str = """
episodes:
- scenes:
  - beats:
    - type: action
      content: t1
    duration_estimate: 60s
  - beats:
    - type: action
      content: t2
    duration_estimate: 60s
  - beats:
    - type: action
      content: t3
    duration_estimate: 60s
"""
        result = evaluate_yaml_quality(yaml_str)
        assert result["duration_diversity"] > 0.9
        assert any("duration" in i.lower() for i in result["issues"])

    def test_reports_invalid_yaml(self) -> None:
        result = evaluate_yaml_quality("not: valid: [[[ yaml: [}")
        assert result["valid_yaml"] is False

    def test_detects_too_few_beats(self) -> None:
        yaml_str = """
episodes:
- scenes:
  - beats:
    - type: action
      content: only one
    duration_estimate: 60s
"""
        result = evaluate_yaml_quality(yaml_str)
        assert any("too condensed" in i.lower() or "only" in i.lower() for i in result["issues"])
