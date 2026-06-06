from __future__ import annotations

import json
import logging
import re
from typing import Any

from backend.config import settings
from backend.core.llm import LLMClient
from backend.core.prompts import PREPROCESS_SYSTEM, PREPROCESS_USER, BATCH_PLAN_SYSTEM, BATCH_PLAN_USER

logger = logging.getLogger(__name__)

_DEMO_NARRATIVE: str = "A programmer named Li Wen loses his job and decides to start his own company."
_DEMO_CHARACTERS: list[dict[str, Any]] = [
    {
        "id": "li_wen",
        "name": "Li Wen",
        "role": "protagonist",
        "goal": "Build a successful startup",
        "fear": "Being a failure to his family",
        "arc": "From angry youth to mature leader",
        "voice_style": "Direct, short sentences, self-deprecating",
    },
]
_DEMO_WORLD: dict[str, Any] = {
    "time_period": "Contemporary (2020s)",
    "locations": [{"name": "Shared Office", "description": "A cramped co-working space"}],
    "world_rules": [],
    "key_items": [],
    "culture": {"customs": [], "hierarchy": "Investor > Founder > Employee"},
}
_DEMO_CHAPTERS: list[dict[str, Any]] = [
    {"chapter": "Chapter 1", "title": "The Fall", "summary": "Li Wen is laid off."},
    {"chapter": "Chapter 2", "title": "The Spark", "summary": "Li Wen decides to start his own business."},
    {"chapter": "Chapter 3", "title": "The Grind", "summary": "Early struggles of entrepreneurship."},
]
_DEMO_EPISODES: list[dict[str, Any]] = [
    {
        "episode": 1,
        "title": "Pilot",
        "logline": "A layoff sparks an unexpected journey.",
        "beats": ["Li Wen gets fired", "Discovers betrayal", "Makes a decision"],
        "character_focus": ["li_wen"],
        "hook": "Will he take the leap?",
    },
    {
        "episode": 2,
        "title": "First Steps",
        "logline": "Li Wen builds his first prototype.",
        "beats": ["Raises seed money", "Assembles a team", "First setback"],
        "character_focus": ["li_wen"],
        "hook": "An investor makes a surprising offer.",
    },
]


def preprocess_novel(text: str, mode: str = "long") -> dict[str, Any]:
    client = LLMClient()
    text_trimmed = text[: settings.MAX_INPUT_CHARS]
    try:
        response = client.generate(
            prompt=PREPROCESS_USER.format(text=text_trimmed, mode=mode),
            system_prompt=PREPROCESS_SYSTEM,
            max_tokens=4096,
            temperature=0.5,
        )
        return parse_json_response(response) or {
            "narrative_summary": _DEMO_NARRATIVE,
            "characters": _DEMO_CHARACTERS,
            "world": _DEMO_WORLD,
            "chapter_outline": _DEMO_CHAPTERS,
        }
    except Exception as e:
        logger.warning("Preprocess LLM call failed, using demo data: %s", e)
        return _get_demo_preprocess_data()


def batch_plan_episodes(
    narrative: str,
    characters: list[dict[str, Any]],
    num_episodes: int,
    mode: str = "long",
) -> list[dict[str, Any]]:
    client = LLMClient()
    chars_text = json.dumps(characters, ensure_ascii=False, indent=2)
    try:
        response = client.generate(
            prompt=BATCH_PLAN_USER.format(
                num_episodes=num_episodes,
                narrative=narrative,
                characters=chars_text,
                mode=mode,
            ),
            system_prompt=BATCH_PLAN_SYSTEM,
            max_tokens=4096,
            temperature=0.7,
        )
        result = parse_json_response(response)
        if isinstance(result, list):
            return result
        return _DEMO_EPISODES[:num_episodes]
    except Exception as e:
        logger.warning("Batch plan failed, using demo data: %s", e)
        return _DEMO_EPISODES[:num_episodes]


def parse_json_response(response: str) -> Any:
    for extractor in (
        _extract_json_block,
        _extract_json_braces,
        _extract_json_brackets,
    ):
        try:
            result = extractor(response)
            if result is not None:
                return result
        except (json.JSONDecodeError, ValueError):
            continue
    return None


def _extract_json_block(text: str) -> Any | None:
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        return json.loads(match.group(1).strip())
    return None


def _extract_json_braces(text: str) -> Any | None:
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                return json.loads(text[start : i + 1])
    return None


def _extract_json_brackets(text: str) -> Any | None:
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == "[":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0 and start >= 0:
                return json.loads(text[start : i + 1])
    return None


def parse_chapters(text: str) -> list[dict[str, str]]:
    pattern = (
        r"(?:^第\s*[零一二三四五六七八九十百千\d]+\s*[章节卷][^\n]*"
        r"|^第\s*\d+\s*节[^\n]*"
        r"|^Chapter\s+\d+[^\n]*"
        r"|^Part\s+\d+[^\n]*"
        r"|^Book\s+\d+[^\n]*"
        r"|^[一二三四五六七八九十]+、[^\n]*)"
    )
    flags = re.MULTILINE | re.IGNORECASE
    matches = list(re.finditer(pattern, text, flags=flags))
    chapters: list[dict[str, str]] = []

    for j, match in enumerate(matches):
        title = match.group().strip()
        start = match.end()
        end = matches[j + 1].start() if j + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        if len(content) >= 20:
            chapters.append({"title": title, "content": content})

    if chapters:
        return chapters

    parts = re.split(r"\n{3,}", text)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) >= 2:
        for idx, part in enumerate(parts, 1):
            if len(part) >= 20:
                lines = part.split("\n", 1)
                title = lines[0].strip()
                content = lines[1].strip() if len(lines) > 1 else part
                chapters.append({"title": title, "content": content})

    if not chapters:
        chapters.append({"title": "全文", "content": text.strip()})

    return chapters


def estimate_tokens(text: str) -> int:
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return len(text) // 2


def detect_language(text: str) -> str:
    if not text:
        return "english"
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    ratio = chinese_chars / len(text)
    if ratio > 0.15:
        return "chinese"
    if ratio > 0.05:
        return "mixed"
    return "english"


def chunk_paragraphs(text: str, max_chars: int = 500) -> list[dict[str, str]]:
    paragraphs = re.split(r"\n\s*\n", text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    if not paragraphs:
        return []
    chunks: list[dict[str, str]] = []
    current: list[str] = []
    current_size = 0
    chunk_num = 0
    for para in paragraphs:
        para_size = len(para)
        if current_size + para_size > max_chars and current:
            chunk_num += 1
            chunks.append({"text": "\n\n".join(current), "source": f"chunk_{chunk_num}"})
            current = []
            current_size = 0
        current.append(para)
        current_size += para_size
    if current:
        chunk_num += 1
        chunks.append({"text": "\n\n".join(current), "source": f"chunk_{chunk_num}"})
    return chunks


def extract_named_entities(text: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {"characters": [], "locations": []}
    lang = detect_language(text)

    if lang in ("chinese", "mixed"):
        import collections

        common_words: set[str] = {
            "我们", "他们", "自己", "什么", "没有", "可以", "已经", "因为", "所以",
            "但是", "如果", "虽然", "而且", "这个", "那个", "这里", "那里", "一个",
            "一下", "一切", "一直", "一样", "不会", "不能", "不过", "不是",
        }
        clean = "".join(ch for ch in text if "\u4e00" <= ch <= "\u9fff")
        seqs: collections.Counter[str] = collections.Counter()
        for size in (2, 3, 4):
            for i in range(len(clean) - size + 1):
                seq = clean[i : i + size]
                if seq not in common_words:
                    seqs[seq] += 1
        top = [(s, c) for s, c in seqs.most_common(50) if c >= 2]
        result["characters"] = [s for s, _ in top[:20]]

        loc_seqs: collections.Counter[str] = collections.Counter()
        location_suffixes = [
            "村", "镇", "城", "市", "省", "国", "山", "河", "湖", "海",
            "森林", "平原", "学院", "广场", "宫殿", "王国", "帝国",
        ]
        for suf in location_suffixes:
            loc_pattern = re.compile(rf"[\u4e00-\u9fff]{{0,3}}{re.escape(suf)}")
            for match in loc_pattern.finditer(text):
                loc_seqs[match.group()] += 1
        result["locations"] = [s for s, c in loc_seqs.most_common(20) if c >= 1]

    if lang in ("english", "mixed"):
        capital_pattern = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+))\b")
        name_counts: dict[str, int] = {}
        for match in capital_pattern.finditer(text):
            name = match.group(1)
            name_counts[name] = name_counts.get(name, 0) + 1
        if lang == "english":
            top_en = [(n, c) for n, c in sorted(name_counts.items(), key=lambda x: -x[1])[:20] if c >= 1]
            result["characters"] = [n for n, _ in top_en]

    return result


def detect_key_points(text: str) -> dict[str, Any]:
    """Extract critical structural hints for guiding LLM generation.

    Returns a dict with:
      - dialogues: first 10 quoted dialogue sentences found
      - time_location_pairs: regex matches of time+location patterns
      - first_chars: first 200 chars of text
      - last_chars: last 200 chars of text
      - ending_sentences: last 3 sentences (split by 。.!?！？)
      - frequent_locations: top 5 location-like nouns
      - must_preserve: combined "checklist" string for prompt injection
    """
    result: dict[str, Any] = {
        "dialogues": [],
        "time_location_pairs": [],
        "first_chars": text[:200].strip(),
        "last_chars": text[-200:].strip(),
        "ending_sentences": [],
        "frequent_locations": [],
        "must_preserve": "",
    }

    # 1. Extract dialogue sentences
    dialogue_pattern = re.compile(r'[""]([^""]+)[""]|\u201c([^\u201d]+)\u201d|"([^"]+)"')
    dialogues = []
    for m in dialogue_pattern.finditer(text):
        content = m.group(1) or m.group(2) or m.group(3)
        if content and len(content) > 3:
            dialogues.append(content.strip())
            if len(dialogues) >= 10:
                break
    result["dialogues"] = dialogues

    # 2. Time + location pairs
    time_words = ["夜", "白天", "清晨", "傍晚", "凌晨", "晚上", "傍晚", "三天后", "一周后", "第二天", "次日",
                  "night", "morning", "evening", "dawn", "dusk", "afternoon", "later", "next day"]
    loc_suffix = ["里", "内", "中", "外", "边", "上", "下", "楼", "室", "房间", "工作间", "厨房", "机房", "平台"]
    pairs = []
    for tw in time_words:
        pattern = re.compile(rf"{re.escape(tw)}.*?([\u4e00-\u9fff]{{2,10}}(?:{'|'.join(re.escape(s) for s in loc_suffix)}))")
        for m in pattern.finditer(text):
            pairs.append({"time": tw, "location": m.group(1)})
            if len(pairs) >= 8:
                break
    result["time_location_pairs"] = pairs

    # 3. Ending sentences
    sentences = re.split(r"[。！？.!?\n]", text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
    result["ending_sentences"] = sentences[-3:] if len(sentences) >= 3 else sentences

    # 4. Build "must preserve" checklist
    parts = []
    parts.append(f"文本开头: {result['first_chars'][:100]}")
    parts.append(f"文本结尾: {result['last_chars'][:100]}")
    if dialogues:
        parts.append(f"关键对话: {'; '.join(dialogues[:5])}")
    if result["ending_sentences"]:
        parts.append(f"结尾: {result['ending_sentences'][-1]}")
    result["must_preserve"] = "\n".join(parts)

    return result


def evaluate_yaml_quality(yaml_content: str) -> dict[str, Any]:
    """Auto-evaluate generated screenplay YAML quality without reference text.

    Returns:
      - valid_yaml: whether YAML can be parsed
      - emotion_null_rate: fraction of beats with emotion=null
      - char_id_null_rate: fraction of dialogue beats missing character_id
      - duration_diversity: Gini-like score (1.0 = all same, 0.0 = varied)
      - scene_count: total scenes
      - beat_count: total beats
      - issues: list of human-readable issue descriptions
    """
    import yaml
    from collections import Counter

    issues: list[str] = []
    result: dict[str, Any] = {
        "valid_yaml": False,
        "emotion_null_rate": 1.0,
        "char_id_null_rate": 1.0,
        "duration_diversity": 1.0,
        "scene_count": 0,
        "beat_count": 0,
        "issues": issues,
    }

    try:
        data = yaml.safe_load(yaml_content)
        result["valid_yaml"] = True
    except Exception as e:
        issues.append(f"YAML parse error: {e}")
        return result

    if not isinstance(data, dict):
        issues.append("YAML root is not a dict")
        return result

    # Count beats, emotions, character_ids
    total_beats = 0
    null_emotions = 0
    null_char_ids = 0
    dialogue_beats = 0
    durations: list[int] = []

    episodes = data.get("episodes", [])
    if not isinstance(episodes, list):
        episodes = []
    result["scene_count"] = sum(len(ep.get("scenes", [])) if isinstance(ep, dict) else 0 for ep in episodes)

    for ep in episodes:
        if not isinstance(ep, dict):
            continue
        for sc in ep.get("scenes", []) or []:
            if not isinstance(sc, dict):
                continue
            dur = sc.get("duration_estimate", "")
            if isinstance(dur, str):
                dnum = re.sub(r"[^0-9]", "", dur)
                if dnum:
                    durations.append(int(dnum))
            for b in sc.get("beats", []) or []:
                if not isinstance(b, dict):
                    continue
                total_beats += 1
                if b.get("emotion") in (None, "", "null"):
                    null_emotions += 1
                if b.get("type") == "dialogue":
                    dialogue_beats += 1
                    if b.get("character_id") in (None, "", "null"):
                        null_char_ids += 1

    result["beat_count"] = total_beats

    if total_beats > 0:
        result["emotion_null_rate"] = round(null_emotions / total_beats, 3)
    if dialogue_beats > 0:
        result["char_id_null_rate"] = round(null_char_ids / dialogue_beats, 3)

    if total_beats <= 3:
        issues.append(f"Only {total_beats} beats total — scenes may be too condensed")

    if result["emotion_null_rate"] > 0.5:
        issues.append(f"Emotion missing in {result['emotion_null_rate']:.0%} of beats")
    if dialogue_beats > 0 and result["char_id_null_rate"] > 0.5:
        issues.append(f"character_id missing in {result['char_id_null_rate']:.0%} of dialogue beats")

    # Duration diversity
    dur_counter = Counter(str(d) for d in durations)
    if dur_counter and len(durations) > 1:
        total = sum(dur_counter.values())
        result["duration_diversity"] = round(sum((v / total) ** 2 for v in dur_counter.values()), 3)
        if result["duration_diversity"] > 0.9:
            issues.append("All scenes have nearly identical durations — should vary by complexity")

    if not issues:
        issues.append("No quality issues detected")

    return result


def _get_demo_preprocess_data() -> dict[str, Any]:
    return {
        "narrative_summary": _DEMO_NARRATIVE,
        "characters": _DEMO_CHARACTERS,
        "world": _DEMO_WORLD,
        "chapter_outline": _DEMO_CHAPTERS,
    }
