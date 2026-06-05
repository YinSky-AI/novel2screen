"""
Fast preprocessor: one LLM call replaces NarrativeAgent + CharacterAgent + WorldAgent.
Reduces 3+ sequential calls to 1, dramatically improving speed.
"""
import json
import re
from .llm import llm_client
from .prompts import PREPROCESS_SYSTEM, PREPROCESS_USER, BATCH_PLAN_SYSTEM, BATCH_PLAN_USER


def preprocess_novel(chapters: list[str]) -> dict:
    """Extract all narrative, character, and world info in ONE LLM call."""
    # Build chapter text with compact formatting
    chapter_lines = []
    for i, ch in enumerate(chapters):
        # Truncate each chapter to ~1500 chars to keep prompt small
        truncated = ch[:1500] + ("..." if len(ch) > 1500 else "")
        chapter_lines.append(f"Chapter {i+1}:\n{truncated}")
    chapters_text = "\n\n---\n\n".join(chapter_lines)

    response = llm_client.complete(
        system_prompt=PREPROCESS_SYSTEM,
        user_prompt=PREPROCESS_USER.format(chapters_text=chapters_text),
        temperature=0.2,
    )

    # Parse JSON from response
    text = response.strip()
    # Strip markdown fences
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON object
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            data = json.loads(match.group())
        else:
            raise

    return {
        "theme": data.get("theme", ""),
        "major_events": data.get("major_events", []),
        "turning_points": data.get("turning_points", []),
        "characters": data.get("characters", []),
        "locations": data.get("locations", []),
    }


def batch_plan_episodes(preprocess_result: dict, mode: str) -> dict:
    """Plan ALL episodes and scenes in ONE LLM call."""
    response = llm_client.complete(
        system_prompt=BATCH_PLAN_SYSTEM,
        user_prompt=BATCH_PLAN_USER.format(
            theme=preprocess_result.get("theme", ""),
            characters=json.dumps(preprocess_result.get("characters", []), ensure_ascii=False),
            major_events=json.dumps(preprocess_result.get("major_events", []), ensure_ascii=False),
            turning_points=json.dumps(preprocess_result.get("turning_points", []), ensure_ascii=False),
            locations=json.dumps(preprocess_result.get("locations", []), ensure_ascii=False),
            mode=mode,
        ),
        temperature=0.4,
    )

    text = response.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise
