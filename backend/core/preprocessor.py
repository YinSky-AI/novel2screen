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
    pattern = r"(?:第[零一二三四五六七八九十百千\d]+章|Chapter\s+\d+)[^\n]*"
    chapters: list[dict[str, str]] = []
    splits = re.split(f"({pattern})", text)
    if len(splits) < 3:
        return [{"title": "Full Text", "content": text}]
    for i in range(1, len(splits), 2):
        title = splits[i].strip()
        content = splits[i + 1].strip() if i + 1 < len(splits) else ""
        chapters.append({"title": title, "content": content})
    return chapters


def estimate_tokens(text: str) -> int:
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return len(text) // 2


def detect_language(text: str) -> str:
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    if chinese_chars > len(text) * 0.15:
        return "chinese"
    return "english"


def smart_chunk(text: str, max_tokens: int | None = None, overlap: int | None = None) -> list[str]:
    if max_tokens is None:
        max_tokens = settings.CHUNK_SIZE
    if overlap is None:
        overlap = settings.CHUNK_OVERLAP
    paragraphs = text.split("\n")
    chunks: list[str] = []
    current: list[str] = []
    current_size = 0
    for para in paragraphs:
        para_size = len(para)
        if current_size + para_size > max_tokens and current:
            chunks.append("\n".join(current))
            overlap_start = max(0, len(current) - max(1, overlap // (max(1, current_size // max(1, len(current))))))
            current = current[overlap_start:]
            current_size = sum(len(p) for p in current)
        current.append(para)
        current_size += para_size
    if current:
        chunks.append("\n".join(current))
    return chunks or [text]


def _get_demo_preprocess_data() -> dict[str, Any]:
    return {
        "narrative_summary": _DEMO_NARRATIVE,
        "characters": _DEMO_CHARACTERS,
        "world": _DEMO_WORLD,
        "chapter_outline": _DEMO_CHAPTERS,
    }
