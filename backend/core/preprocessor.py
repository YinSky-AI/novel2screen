"""
Fast preprocessor: one LLM call replaces NarrativeAgent + CharacterAgent + WorldAgent.
Supports RAG injection for long novels via SemanticMemory.
"""
import json
import re
from .llm import llm_client
from .prompts import PREPROCESS_SYSTEM, PREPROCESS_USER, PREPROCESS_USER_WITH_RAG
from ..config import CHUNK_SIZE, TOP_K_SHORT, TOP_K_LONG, RAG_ENABLED


def preprocess_novel(chapters: list[str], semantic_memory=None, mode: str = "short") -> dict:
    """Extract all narrative, character, and world info in ONE LLM call with optional RAG."""
    chapter_lines = []
    total_chars = 0
    top_k = TOP_K_LONG if mode == "long" else TOP_K_SHORT

    for i, ch in enumerate(chapters):
        truncated = ch[:CHUNK_SIZE] + ("..." if len(ch) > CHUNK_SIZE else "")
        chapter_lines.append(f"Chapter {i+1}:\n{truncated}")
        total_chars += len(ch)
    chapters_text = "\n\n---\n\n".join(chapter_lines)

    rag_context = ""
    if RAG_ENABLED and semantic_memory and total_chars > 5000:
        try:
            rag_context = semantic_memory.retrieve_context(
                queries=["main character motivation", "key plot events", "central conflict", "setting description"],
                top_k=top_k,
            )
        except Exception:
            pass

    if rag_context:
        user_prompt = PREPROCESS_USER_WITH_RAG.format(chapters_text=chapters_text, rag_context=rag_context)
    else:
        user_prompt = PREPROCESS_USER.format(chapters_text=chapters_text)

    response = llm_client.complete(
        system_prompt=PREPROCESS_SYSTEM,
        user_prompt=user_prompt,
        temperature=0.2,
    )

    return _parse_json_response(response)


def batch_plan_episodes(preprocess_result: dict, mode: str, semantic_memory=None) -> dict:
    """Plan ALL episodes and scenes in ONE LLM call with optional RAG."""
    from .prompts import BATCH_PLAN_SYSTEM, BATCH_PLAN_USER, BATCH_PLAN_USER_WITH_RAG

    top_k = TOP_K_LONG if mode == "long" else TOP_K_SHORT

    rag_context = ""
    if RAG_ENABLED and semantic_memory:
        try:
            theme = preprocess_result.get("theme", "")
            characters_info = " ".join(
                c.get("name", "") + " " + c.get("goal", "")
                for c in preprocess_result.get("characters", [])
            )
            rag_context = semantic_memory.retrieve_context(
                queries=[theme, characters_info, "climax scene", "emotional turning point"],
                top_k=top_k,
            )
        except Exception:
            pass

    if rag_context:
        user_prompt_batch = BATCH_PLAN_USER_WITH_RAG.format(
            theme=preprocess_result.get("theme", ""),
            characters=json.dumps(preprocess_result.get("characters", []), ensure_ascii=False),
            major_events=json.dumps(preprocess_result.get("major_events", []), ensure_ascii=False),
            turning_points=json.dumps(preprocess_result.get("turning_points", []), ensure_ascii=False),
            locations=json.dumps(preprocess_result.get("locations", []), ensure_ascii=False),
            mode=mode,
            rag_context=rag_context,
        )
    else:
        user_prompt_batch = BATCH_PLAN_USER.format(
            theme=preprocess_result.get("theme", ""),
            characters=json.dumps(preprocess_result.get("characters", []), ensure_ascii=False),
            major_events=json.dumps(preprocess_result.get("major_events", []), ensure_ascii=False),
            turning_points=json.dumps(preprocess_result.get("turning_points", []), ensure_ascii=False),
            locations=json.dumps(preprocess_result.get("locations", []), ensure_ascii=False),
            mode=mode,
        )

    response = llm_client.complete(
        system_prompt=BATCH_PLAN_SYSTEM,
        user_prompt=user_prompt_batch,
        temperature=0.4,
    )

    return _json_parse_strict(response)


def _parse_json_response(text: str) -> dict:
    """Parse JSON from LLM response with markdown fence stripping."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
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


def _json_parse_strict(text: str) -> dict:
    """Parse JSON strictly, returning empty dict on failure."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {}
