from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

import pytest

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


class MockLLMClient:
    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: dict[str, str] | None = None,
    ) -> str:
        full = " ".join(m.get("content", "") for m in messages)
        return self._respond(full)

    def extract_json(self, text: str) -> dict[str, Any]:
        return json.loads(text) if text.strip() else {}

    def repair_json(self, text: str) -> str:
        return text

    @staticmethod
    def _respond(prompt: str) -> str:
        if "episode planner" in prompt.lower() or "Plan a TV series adaptation" in prompt:
            return json.dumps({
                "episodes": [
                    {"id": "ep_001", "title": "Pilot", "summary": "The journey begins.", "key_events": ["e1"], "characters_featured": ["Hero"], "emotional_arc": "Hope", "cliffhanger": "???"},
                ],
                "season_arc": "Hero wins",
            }, ensure_ascii=False)
        if "scene planner" in prompt.lower() or "Plan individual scenes for episode" in prompt:
            return json.dumps({
                "episode_id": "ep_001",
                "scenes": [
                    {"scene_id": "sc_001", "location": "Home", "time": "Morning", "visual_focus": "Window", "sound_effect": "Wind", "voice_over": None, "transition": "cut", "duration_estimate": "60s",
                     "beats": [{"type": "dialogue", "character_id": "char_001", "content": "Hello", "emotion": "hopeful"}]},
                ],
            }, ensure_ascii=False)
        if "story timeline" in prompt.lower() or "timeline of events for screenplay" in prompt:
            return json.dumps({
                "events": [
                    {"order": 1, "description": "Start", "characters_involved": ["Hero"], "location": "Home", "emotional_beat": "Hope", "estimated_screen_time": 5},
                ],
                "timeline_type": "linear",
                "major_turning_points": ["The reveal"],
            }, ensure_ascii=False)
        if "world-building" in prompt.lower() or "world-building specialist" in prompt:
            return json.dumps({
                "locations": [{"name": "Home", "description": "A room", "significance": "Start", "visual_suggestions": "Warm light"}],
                "world_rules": [],
                "atmosphere": "Cozy",
            }, ensure_ascii=False)
        if "character analyst" in prompt.lower() or "identify all characters" in prompt:
            return json.dumps({
                "characters": [
                    {"id": "char_001", "name": "Hero", "role": "protagonist", "goal": "Win", "fear": "Lose", "arc": "Growth", "voice_style": "bold"},
                ],
            }, ensure_ascii=False)
        if "screenplay analyst" in prompt.lower() or "narrative structure" in prompt:
            return json.dumps({
                "title": "Test Story",
                "logline": "A hero's journey.",
                "genre": "drama",
                "theme": "courage",
                "major_events": [{"chapter": 1, "event": "Hero begins journey", "characters_involved": ["Hero"]}],
                "subplots": [],
            }, ensure_ascii=False)
        if "Score each category" in prompt or "quality assessment" in prompt:
            return json.dumps({"score": 8.0, "issues": [], "suggestions": [], "overall_assessment": "Good"}, ensure_ascii=False)
        if "repaired_yaml" in prompt or "Repair the following" in prompt:
            return json.dumps({"repaired_yaml": "title: Test\nlogline: A test.\ngenre: drama\ntheme: courage\ncharacters: []\nepisodes: []", "changes_made": [], "validation_passed": True}, ensure_ascii=False)
        if "consistency" in prompt.lower() or "Compare the edited screenplay" in prompt:
            return json.dumps({"consistent": True, "issues": [], "resolved": True}, ensure_ascii=False)
        return "{}"


class MockSettings:
    CHUNK_SIZE = 1500
    CHUNK_OVERLAP = 200


def _make_memory() -> MagicMock:
    m = MagicMock()
    m.semantic = MagicMock()
    m.semantic.index = MagicMock()
    m.semantic.retrieve_context = MagicMock(return_value="")
    return m


class TestE2EPipeline:
    def test_fast_pipeline_chinese_novel(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from backend.workflows.novel2screen import Novel2ScreenWorkflow

        monkeypatch.setattr(
            "backend.core.preprocessor.chunk_paragraphs",
            lambda text, max_chars=500: [{"text": text[i:i+max_chars], "source": f"chunk_{i//max_chars+1}"} for i in range(0, len(text), max_chars)],
        )

        wf = Novel2ScreenWorkflow(MockSettings(), MockLLMClient(), _make_memory())
        result = wf.fast_run(SAMPLE_CN)
        assert result["status"] == "completed"
        yaml_content = result["yaml_content"]
        assert "scenes:" in yaml_content
        assert "sc_001" in yaml_content
        assert "scenes: []" not in yaml_content
        assert "title" in yaml_content.lower()

    def test_fast_pipeline_english_novel(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from backend.workflows.novel2screen import Novel2ScreenWorkflow

        monkeypatch.setattr(
            "backend.core.preprocessor.chunk_paragraphs",
            lambda text, max_chars=500: [{"text": text[i:i+max_chars], "source": f"chunk_{i//max_chars+1}"} for i in range(0, len(text), max_chars)],
        )

        wf = Novel2ScreenWorkflow(MockSettings(), MockLLMClient(), _make_memory())
        result = wf.fast_run(SAMPLE_EN)
        assert result["status"] == "completed"
        yaml_content = result["yaml_content"]
        assert "scenes:" in yaml_content
        assert "sc_001" in yaml_content
        assert "scenes: []" not in yaml_content
        assert "title" in yaml_content.lower()

    def test_full_pipeline(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from backend.workflows.novel2screen import Novel2ScreenWorkflow

        monkeypatch.setattr(
            "backend.core.preprocessor.chunk_paragraphs",
            lambda text, max_chars=500: [{"text": text[i:i+max_chars], "source": f"chunk_{i//max_chars+1}"} for i in range(0, len(text), max_chars)],
        )

        wf = Novel2ScreenWorkflow(MockSettings(), MockLLMClient(), _make_memory())
        result = wf.run(SAMPLE_CN[:500])
        assert result["status"] == "completed"
        assert len(result["yaml_content"]) > 0


