"""Pipeline orchestrator for Novel2Screen.

Defines a stage-based pipeline abstraction. Each stage is a discrete processing
unit with run/validate/repair. Pipelines compose stages into directed flows.

Two built-in pipelines:
  - fast:  2-3 LLM calls (preprocess → batch_plan → quick_critic)
  - full:  9+ agent chain (narrative → character → world → timeline → ...)
"""
from __future__ import annotations

import json
import re
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


class RetryAction(Enum):
    """What to change when a stage fails."""

    RESET = "reset"                      # Same input, no change
    LOWER_TEMP = "lower_temperature"     # Decrease creativity
    TRUNCATE_INPUT = "truncate_input"    # Cut input to fit context
    SKIP_STAGE = "skip_stage"            # Skip stage, use default output
    FALLBACK_CHUNK = "fallback_chunk"    # Process in smaller chunks


@dataclass
class StageResult:
    """Result of a single stage execution."""

    stage_name: str
    success: bool
    output: Any = None
    error: str = ""
    attempts: int = 1
    retry_action: RetryAction | None = None


@dataclass
class PipelineState:
    """Mutable state flowing through all pipeline stages."""

    # Input
    novel_text: str = ""
    novel_title: str = ""
    genre: str = ""
    language: str = "en"

    # Parsed
    chapters: list[dict] = field(default_factory=list)
    num_chapters: int = 0

    # Stage outputs
    narrative: dict = field(default_factory=dict)
    characters: dict = field(default_factory=dict)
    world: dict = field(default_factory=dict)
    timeline: dict = field(default_factory=dict)
    episode_plan: dict = field(default_factory=dict)
    scene_plans: list[dict] = field(default_factory=list)
    dialogue_scenes: list[dict] = field(default_factory=list)
    screenplay_yaml: str = ""
    screenplay: dict = field(default_factory=dict)

    # Critic / Repair
    violations: list[dict] = field(default_factory=list)
    critic_score: float = 1.0
    repair_changes: list[str] = field(default_factory=list)

    # Novel context
    novel_ending: str = ""
    reference_characters: list[dict] = field(default_factory=list)

    # Status
    error: str = ""
    completed: bool = False
    pipeline_name: str = "fast"
    stages_completed: list[str] = field(default_factory=list)
    stage_results: dict[str, StageResult] = field(default_factory=dict)


@dataclass
class Stage:
    """A single processing stage in the pipeline."""

    name: str
    run_fn: Callable[[PipelineState], Any]
    validate_fn: Callable[[Any], bool] | None = None
    repair_fn: Callable[[Any, list[str]], Any] | None = None
    default_output: Any = None
    max_retries: int = 2
    temperature: float = 0.3
    retry_temp_drop: float = 0.1  # How much to lower temp on retry
    skip_on_failure: bool = False  # If True, use default_output instead of failing

    def execute(self, state: PipelineState) -> StageResult:
        """Run the stage with retry logic."""
        last_error = None
        temp = self.temperature
        result = None

        for attempt in range(self.max_retries + 1):
            try:
                result = self.run_fn(state)
                if self.validate_fn and not self.validate_fn(result):
                    raise ValueError(f"Validation failed for stage '{self.name}'")
                return StageResult(
                    stage_name=self.name,
                    success=True,
                    output=result,
                    attempts=attempt + 1,
                )
            except Exception as e:
                last_error = str(e)
                if attempt < self.max_retries:
                    temp = max(0.05, temp - self.retry_temp_drop)

        # All retries exhausted
        action = RetryAction.SKIP_STAGE if self.skip_on_failure else RetryAction.RESET
        return StageResult(
            stage_name=self.name,
            success=False,
            output=self.default_output,
            error=last_error,
            attempts=self.max_retries + 1,
            retry_action=action,
        )


class Pipeline:
    """A directed graph of stages executed in order."""

    def __init__(self, name: str, stages: list[Stage]):
        self.name = name
        self.stages = stages

    def run(self, state: PipelineState) -> PipelineState:
        """Execute all stages in order."""
        for stage in self.stages:
            result = stage.execute(state)
            state.stage_results[stage.name] = result
            state.stages_completed.append(stage.name)

            # Always store output (even on skip, so downstream sees default_output)
            if isinstance(result.output, dict):
                setattr(state, stage.name, result.output)

            if not result.success:
                if result.retry_action == RetryAction.SKIP_STAGE:
                    continue
                if result.retry_action == RetryAction.FALLBACK_CHUNK:
                    fallback_result = self._run_fallback(state, stage)
                    if not fallback_result.success:
                        state.error = f"Pipeline failed at stage '{stage.name}': {result.error}"
                        return state
                else:
                    state.error = f"Pipeline failed at stage '{stage.name}': {result.error}"
                    return state

        state.completed = True
        return state

    def _run_fallback(self, state: PipelineState, failed_stage: Stage) -> StageResult:
        """Fallback: truncate chapters to half then retry once."""
        try:
            import copy
            fb_state = copy.copy(state)
            if fb_state.chapters and len(fb_state.chapters) > 5:
                half = max(len(fb_state.chapters) // 2, 3)
                fb_state.chapters = fb_state.chapters[:half]
                fb_state.num_chapters = len(fb_state.chapters)
            result = failed_stage.run_fn(fb_state)
            if failed_stage.validate_fn and not failed_stage.validate_fn(result):
                return StageResult(
                    stage_name=failed_stage.name,
                    success=False,
                    error="Fallback also failed",
                    attempts=1,
                )
            return StageResult(
                stage_name=failed_stage.name,
                success=True,
                output=result,
                attempts=1,
            )
        except Exception as e:
            return StageResult(
                stage_name=failed_stage.name,
                success=False,
                error=f"Fallback error: {e}",
                attempts=1,
            )


def build_state(novel_text: str, novel_title: str = "", genre: str = "",
                language: str = "", pipeline: str = "fast") -> PipelineState:
    """Build initial PipelineState from input."""
    from .novel_reader import detect_language, extract_ending, parse_chapters

    if not language:
        language = detect_language(novel_text)

    chapters = parse_chapters(novel_text)
    ending = extract_ending(novel_text)

    return PipelineState(
        novel_text=novel_text,
        novel_title=novel_title or "Untitled",
        genre=genre or "Drama",
        language=language,
        chapters=chapters,
        num_chapters=len(chapters),
        novel_ending=ending,
        pipeline_name=pipeline,
    )


# ── Fast Pipeline Stage Definitions ──

def _stage_parse(state: PipelineState) -> dict:
    """Stage 1: Parse and analyze the novel."""
    from .novel_reader import summarize_chapters
    return {
        "chapters": state.chapters,
        "chapter_count": state.num_chapters,
        "summary": summarize_chapters(state.chapters),
        "language": state.language,
    }

def _stage_preprocess(state: PipelineState) -> dict:
    """Stage 2: Extract narrative + characters + world in one LLM call."""
    from backend.config import RAG_ENABLED
    from backend.core.memory import SemanticMemory
    from backend.core.preprocessor import preprocess_novel

    chapters_text = [c["content"] for c in state.chapters]

    sem_mem = None
    if RAG_ENABLED:
        try:
            sem_mem = SemanticMemory(persist_dir="data/chroma_db")
            sem_mem.index(state.novel_text, source_label="novel")
        except Exception:
            pass

    result = preprocess_novel(chapters_text, semantic_memory=sem_mem,
                              mode="short" if state.num_chapters <= 10 else "long")
    n_chars = len(result.get("characters", []))
    n_events = len(result.get("major_events", []))
    theme = result.get("theme", "")[:60]
    print(f"[Pipeline] preprocess done: theme='{theme}', chars={n_chars}, events={n_events}")
    if result.get("characters"):
        state.reference_characters = result["characters"]
    # 原文一致性检测：清洗 LLM 输出的角色和地点
    try:
        from .fidelity import detect_hallucinated_characters, detect_hallucinated_locations
        suspicious_chars = detect_hallucinated_characters(result.get("characters", []), state.novel_text, state.language)
        suspicious_locs = detect_hallucinated_locations(result.get("locations", []), state.novel_text)
        for sc in suspicious_chars:
            state.violations.append({"category": "character_fidelity", "severity": "warning",
                "description": f"Character '{sc['name']}' ({sc.get('id','')}) - {sc['reason']}"})
        for sl in suspicious_locs:
            state.violations.append({"category": "location_fidelity", "severity": "warning",
                "description": f"Location '{sl['name']}' - {sl['reason']}"})
        if suspicious_chars and len(suspicious_chars) > len(result.get("characters", [])) * 0.5:
            state.violations.append({"category": "character_fidelity", "severity": "error",
                "description": f"More than half of characters ({len(suspicious_chars)}/{len(result.get('characters',[]))}) may be fabricated"})
    except Exception:
        pass
    return result

def _validate_preprocess(output: dict) -> bool:
    return bool(output.get("theme")) and bool(output.get("characters"))

def _stage_batch_plan(state: PipelineState) -> dict:
    """Stage 3: Plan all episodes + scenes + beats in one LLM call."""
    from backend.config import RAG_ENABLED
    from backend.core.memory import SemanticMemory
    from backend.core.preprocessor import batch_plan_episodes

    # Read from preprocess output (stored as state.preprocess)
    pp = getattr(state, "preprocess", {}) or {}
    if not isinstance(pp, dict):
        pp = {}

    pre = {
        "theme": pp.get("theme", ""),
        "major_events": pp.get("major_events", []),
        "turning_points": pp.get("turning_points", []),
        "characters": pp.get("characters", []),
        "locations": pp.get("locations", []),
    }

    sem_mem = None
    if RAG_ENABLED:
        try:
            sem_mem = SemanticMemory(persist_dir="data/chroma_db")
            sem_mem.index(state.novel_text, source_label="novel")
        except Exception:
            pass

    ep_result = batch_plan_episodes(
        pre,
        mode="short" if state.num_chapters <= 10 else "long",
        semantic_memory=sem_mem,
    )
    n_eps = len(ep_result.get("episodes", []))
    n_scs = sum(len(ep.get("scenes", [])) for ep in ep_result.get("episodes", []))
    print(f"[Pipeline] batch_plan done: episodes={n_eps}, scenes={n_scs}")
    # 原文一致性检测：清洗 LLM 输出的剧集中的 character_id 和 emotion
    try:
        from .fidelity import detect_hallucinated_scene_emotions, validate_character_ids_in_episodes
        from .novel_reader import get_emotion_set
        valid_ids = set()
        if isinstance(state.characters, dict):
            valid_ids = {c["id"] for c in state.characters.get("characters", []) if c.get("id")}
        elif isinstance(getattr(state, "preprocess", {}), dict):
            valid_ids = {c["id"] for c in state.preprocess.get("characters", []) if c.get("id")}
        id_violations = validate_character_ids_in_episodes(ep_result.get("episodes", []), valid_ids)
        for v in id_violations:
            state.violations.append({"category": "character_id_fidelity", "severity": "error", "description": v})
        emo_violations = detect_hallucinated_scene_emotions(ep_result.get("episodes", []), get_emotion_set(state.language))
        for v in emo_violations:
            state.violations.append({"category": "emotion_fidelity", "severity": "warning", "description": v})
    except Exception:
        pass
    return ep_result

def _validate_batch_plan(output: dict) -> bool:
    episodes = output.get("episodes", [])
    return len(episodes) >= 1 and all("scenes" in ep for ep in episodes)

def _stage_critic(state: PipelineState) -> dict:
    """Stage 4: Quick quality check."""
    from backend.core.llm import llm_client
    from backend.core.prompts import FAST_CRITIC_SYSTEM, FAST_CRITIC_USER

    bp = getattr(state, "batch_plan", {}) or {}
    if not isinstance(bp, dict):
        bp = {}
    episodes = bp.get("episodes", [])
    pre = getattr(state, "preprocess", {}) or {}
    if not isinstance(pre, dict):
        pre = {}

    summary_data = {
        "title": state.novel_title,
        "episodes": len(episodes),
        "scenes": sum(len(ep.get("scenes", [])) for ep in episodes),
        "characters": len(pre.get("characters", [])),
        "theme": pre.get("theme", ""),
    }

    critic_resp = llm_client.complete(
        system_prompt=FAST_CRITIC_SYSTEM,
        user_prompt=FAST_CRITIC_USER.format(summary=json.dumps(summary_data, ensure_ascii=False)),
        temperature=0.1,
    )
    critic_text = critic_resp.strip()
    critic_text = re.sub(r"^`(?:json)?\s*", "", critic_text)
    critic_text = re.sub(r"\s*`$", "", critic_text)

    try:
        return json.loads(critic_text)
    except json.JSONDecodeError:
        return {"violations": [], "score": 0.9}

def _normalize_episodes(raw_episodes: list, char_ids: list[str]) -> list:
    """Normalize DeepSeek output to match Pydantic Screenplay schema."""
    if not raw_episodes:
        return []

    # 防御：过滤掉非 dict 的元素（LLM 可能返回字符串等异常数据）
    raw_episodes = [ep for ep in raw_episodes if isinstance(ep, dict)]
    episodes = []
    for i, ep in enumerate(raw_episodes):
        ep_id = ep.get("id")
        if isinstance(ep_id, int):
            ep_id = f"ep_{ep_id:03d}"
        if isinstance(ep_id, str) and ep_id:
            # Normalize: "ep1", "ep_1", "1", "001" → "ep_001"
            import re as _re
            m = _re.match(r"^ep_?(\d+)$", ep_id)
            if m:
                ep_id = f"ep_{int(m.group(1)):03d}"
            elif ep_id.isdigit():
                ep_id = f"ep_{int(ep_id):03d}"
            elif not _re.match(r"^ep_\d{3}$", ep_id):
                ep_id = f"ep_{i+1:03d}"
        else:
            ep_id = f"ep_{i+1:03d}"
        ep_id = str(ep_id)

        scenes = []
        for j, sc in enumerate(ep.get("scenes", [])):
            sc_id = sc.get("scene_id")
            if isinstance(sc_id, int):
                sc_id = f"sc_{sc_id:03d}"
            if isinstance(sc_id, str) and sc_id:
                import re as _re
                m = _re.match(r"^sc_?(\d+)$", sc_id)
                if m:
                    sc_id = f"sc_{int(m.group(1)):03d}"
                elif sc_id.isdigit():
                    sc_id = f"sc_{int(sc_id):03d}"
                elif not _re.match(r"^sc_\d{3}$", sc_id):
                    sc_id = f"sc_{j+1:03d}"
            else:
                sc_id = f"sc_{j+1:03d}"
            sc_id = str(sc_id)

            # DeepSeek outputs: "beats" or "dialogue_beats" or "dialogue"
            beats_raw = sc.get("beats") or sc.get("dialogue_beats") or sc.get("dialogue") or []
            beats = []
            for b in beats_raw:
                cid = b.get("character_id")
                if cid is None:
                    cid = b.get("speaker")
                if isinstance(cid, int):
                    idx = cid - 1
                    cid = char_ids[idx] if 0 <= idx < len(char_ids) else f"char_{cid:03d}"
                if cid and not isinstance(cid, str):
                    cid = str(cid)
                btype = b.get("type", "dialogue" if cid else "action")
                content = b.get("content") or b.get("line") or b.get("description") or b.get("text", "")
                beats.append({
                    "type": btype,
                    "character_id": cid if btype == "dialogue" else (cid or None),
                    "content": str(content),
                    "emotion": b.get("emotion") or b.get("emotion_label"),
                })

            if not beats:
                cid = char_ids[0] if char_ids else None
                beats = [{"type": "action", "character_id": cid, "content": "Scene opens.", "emotion": "calm"}]

            duration = sc.get("duration_estimate") or sc.get("duration", "120s")
            if isinstance(duration, int):
                duration = f"{duration}s"
            duration = str(duration)

            cids = sc.get("characters_present", [])
            if not isinstance(cids, list):
                cids = [str(cids)] if cids else []
            cids = [str(c) for c in cids]

            location = sc.get("location") or sc.get("scene_title") or sc.get("setting", "Unknown")

            scenes.append({
                "scene_id": str(sc_id),
                "location": str(location),
                "time": str(sc.get("time") or sc.get("time_of_day") or "Day"),
                "characters_present": cids,
                "duration_estimate": str(duration),
                "transition": str(sc.get("transition", "cut")),
                "beats": beats,
            })

        summary = ep.get("summary") or ep.get("synopsis") or ep.get("title", "")
        episodes.append({
            "id": str(ep_id),
            "title": str(ep.get("title", f"Episode {i+1}")),
            "summary": str(summary),
            "scenes": scenes,
        })
    return episodes


def _stage_build_screenplay(state: PipelineState) -> dict:
    """Stage 5: Assemble final YAML from all stage outputs."""
    from backend.schemas.models import Screenplay
    from backend.schemas.validator import screenplay_to_yaml

    # Read from preprocess output (stored as state.preprocess)
    pre = getattr(state, "preprocess", {}) or {}
    if not isinstance(pre, dict):
        pre = {}

    chars = pre.get("characters", [])
    if not chars:
        pass
    else:
        # Normalize character IDs
        for i, c in enumerate(chars):
            if not c.get("id") or isinstance(c.get("id"), int):
                c["id"] = f"char_{i+1:03d}"
            if not c.get("traits"):
                c["traits"] = ["Determined"]
            if not c.get("goal"):
                c["goal"] = "Drive the story"
            if not c.get("fear"):
                c["fear"] = "Failure"
            if not c.get("arc"):
                c["arc"] = "Growth"
            if not c.get("voice_style"):
                c["voice_style"] = "Natural"

    # Normalize role field - LLM sometimes returns non-standard values (Chinese, annotated, etc)
    role_map = {
        "protagonist": "protagonist", "主角": "protagonist", "主人": "protagonist", "hero": "protagonist",
        "antagonist": "antagonist", "反派": "antagonist", "敌人": "antagonist", "villain": "antagonist",
        "supporting": "supporting", "配角": "supporting", "辅助": "supporting",
    }
    for c in chars:
        raw_role = str(c.get("role", "")).lower().strip()
        # Strip parenthetical annotations: "antagonist? (blabla)" -> "antagonist?"
        if "(" in raw_role:
            raw_role = raw_role.split("(")[0].strip()
        if "?" in raw_role:
            raw_role = raw_role.split("?")[0].strip()
        if raw_role in role_map:
            c["role"] = role_map[raw_role]
        else:
            c["role"] = "supporting"  # safe fallback

    char_ids = [c["id"] for c in chars]

    theme = pre.get("theme", "")

    # Read from batch_plan output (stored as state.batch_plan)
    bp = getattr(state, "batch_plan", {}) or {}
    if not isinstance(bp, dict):
        bp = {}
    raw_episodes = bp.get("episodes", [])
    raw_episodes = _normalize_episodes(raw_episodes, char_ids)

    if not raw_episodes:
        msg = "No episodes generated. The batch_plan stage produced empty output. Check that your API key is configured properly and the LLM model is accessible."
        raise ValueError(msg)

    lang = state.language

    from .novel_reader import get_emotion_set
    allowed_emotions = get_emotion_set(lang)

    std_emos = {e.lower() for e in allowed_emotions}
    emo_map = {
        "震惊": "surprise", "愤怒": "anger", "恐惧": "fear",
        "悲伤": "sadness", "喜悦": "joy", "怀疑": "tension",
        "专注": "calm", "紧张": "tension", "决心": "resolve",
        "困惑": "confusion", "determined": "resolve",
        "desperation": "fear", "urgency": "tension",
        "suspicion": "tension", "determination": "resolve",
    }

    for ep in raw_episodes:
        ep.setdefault("scenes", [])
        for sc in ep.get("scenes", []):
            if not sc.get("characters_present"):
                cids = list({
                    b.get("character_id") for b in sc.get("beats", [])
                    if b.get("character_id")
                })
                if cids:
                    sc["characters_present"] = cids
            for b in sc.get("beats", []):
                e = b.get("emotion")
                if e:
                    k = e.lower().strip()
                    if k not in std_emos:
                        mapped = emo_map.get(k)
                        if mapped:
                            b["emotion"] = mapped

    screenplay = Screenplay(
        title=state.novel_title,
        logline=theme,
        genre=state.genre,
        theme=theme,
        characters=chars,
        episodes=raw_episodes,
    )
    screenplay_dict = screenplay.model_dump(exclude_none=True)
    raw_yaml = screenplay_to_yaml(screenplay)
    raw_yaml = re.sub(r"^`(?:yaml)?\s*", "", raw_yaml)
    raw_yaml = re.sub(r"\s*`$", "", raw_yaml)

    state.screenplay_yaml = raw_yaml
    state.screenplay = screenplay_dict

    return {
        "screenplay": screenplay_dict,
        "screenplay_yaml": raw_yaml,
    }

def _stage_validate_output(state: PipelineState) -> dict:
    """Stage 6: Validate output against all constraints."""
    from .output_validator import validate_screenplay_output

    yaml_str = state.screenplay_yaml
    if not yaml_str and isinstance(state.screenplay, dict):
        from backend.schemas.validator import screenplay_to_yaml
        try:
            from backend.schemas.models import Screenplay
            sp = Screenplay(**state.screenplay)
            yaml_str = screenplay_to_yaml(sp)
        except Exception:
            pass

    report = validate_screenplay_output(
        yaml_str=yaml_str or "",
        novel_text=state.novel_text,
        novel_ending=state.novel_ending,
        reference_characters=state.reference_characters,
        language=state.language,
    )
    # 完整 fidelity 检测报告
    try:
        from .fidelity import run_fidelity_scrub, summarize_fidelity_report
        bp = getattr(state, "batch_plan", {}) or {}
        pre = getattr(state, "preprocess", {}) or {}
        fid_report = run_fidelity_scrub(
            preprocess_output=pre if isinstance(pre, dict) else {},
            batch_plan_output=bp if isinstance(bp, dict) else {},
            novel_text=state.novel_text,
            language=state.language,
        )
        fid_summary = summarize_fidelity_report(fid_report)
        if fid_report["fidelity_score"] < 1.0:
            state.violations.append({
                "category": "fidelity_summary", "severity": "warning",
                "description": fid_summary,
            })
        state.critic_score = min(state.critic_score, fid_report["fidelity_score"])
    except Exception:
        pass
    return {
        "validation_report": report.to_dict(),
        "violations": report.errors + report.warnings + state.violations,
        "critic_score": state.critic_score,
    }


# ── Pipeline Builders ──

def build_fast_pipeline() -> Pipeline:
    """Build the fast pipeline (2-3 LLM calls)."""
    return Pipeline("fast", [
        Stage("parse", _stage_parse, skip_on_failure=True),
        Stage("preprocess", _stage_preprocess, _validate_preprocess,
              temperature=0.2, max_retries=2, skip_on_failure=True,
              default_output={"theme": "", "major_events": [], "characters": [], "locations": []}),
        Stage("batch_plan", _stage_batch_plan, _validate_batch_plan,
              temperature=0.4, max_retries=2, skip_on_failure=True,
              default_output={"episodes": []}),
        Stage("build_screenplay", _stage_build_screenplay, skip_on_failure=False),
        Stage("critic", _stage_critic, skip_on_failure=True,
              default_output={"violations": [], "score": 0.9}),
        Stage("validate_output", _stage_validate_output, skip_on_failure=True,
              default_output={"validation_report": {"passed": True, "errors": [], "warnings": [], "score": 1.0},
                               "violations": [], "critic_score": 1.0}),
    ])


def build_full_pipeline() -> Pipeline:
    """Build the full agent chain pipeline (9+ LLM calls)."""
    from backend.agents.character import CharacterAgent
    from backend.agents.critic import CriticAgent
    from backend.agents.dialogue import DialogueAgent
    from backend.agents.episode_planner import EpisodePlannerAgent
    from backend.agents.narrative import NarrativeAgent
    from backend.agents.repair import RepairAgent
    from backend.agents.scene_planner import ScenePlannerAgent
    from backend.agents.timeline import TimelineAgent
    from backend.agents.world import WorldAgent

    narrative_agent = NarrativeAgent()
    character_agent = CharacterAgent()
    world_agent = WorldAgent()
    timeline_agent = TimelineAgent()
    episode_planner = EpisodePlannerAgent()
    scene_planner = ScenePlannerAgent()
    dialogue_agent = DialogueAgent()
    CriticAgent()
    RepairAgent()

    def _full_narrative(state: PipelineState) -> dict:
        chunks = [c["content"] for c in state.chapters]
        return narrative_agent.retry({"chunks": chunks})

    def _full_characters(state: PipelineState) -> dict:
        content = state.novel_text[:8000]
        result = character_agent.retry({"content": content})
        if result.get("characters"):
            state.reference_characters = result["characters"]
        return result

    def _full_world(state: PipelineState) -> dict:
        if state.num_chapters <= 10:
            return world_agent.get_default_context()
        return world_agent.retry({"content": state.novel_text[:8000]})

    def _full_timeline(state: PipelineState) -> dict:
        events = []
        if isinstance(state.narrative, dict):
            events = state.narrative.get("major_events", [])
        return timeline_agent.retry({
            "major_events": events,
            "mode": "short" if state.num_chapters <= 10 else "long",
        })

    def _full_episode_plan(state: PipelineState) -> dict:
        chars = []
        if isinstance(state.characters, dict):
            chars = state.characters.get("characters", [])
        return episode_planner.retry({
            "narrative": state.narrative if isinstance(state.narrative, dict) else {},
            "characters": chars,
            "mode": "short" if state.num_chapters <= 10 else "long",
        })

    def _full_scenes_and_dialogue(state: PipelineState) -> dict:
        chars = []
        if isinstance(state.characters, dict):
            chars = state.characters.get("characters", [])
        world_ctx = state.world if isinstance(state.world, dict) else {}
        episodes_raw = []
        if isinstance(state.episode_plan, dict):
            episodes_raw = state.episode_plan.get("episodes", [])

        scene_plans = []
        dialogue_scenes = []

        for ep in episodes_raw:
            ep_id = ep.get("id", "ep_001")
            sp = scene_planner.retry({
                "episode_id": ep_id,
                "episode_title": ep.get("title", ""),
                "episode_summary": ep.get("summary", ""),
                "characters": chars,
                "world_context": world_ctx,
            })
            scene_plans.append(sp)
            for sc_plan in sp.get("scenes", []):
                dialogue = dialogue_agent.retry({
                    "scene_plan": {
                        "scene_id": sc_plan.get("scene_id", "sc_001"),
                        "location": sc_plan.get("location", "Unknown"),
                        "time": sc_plan.get("time", "Unknown"),
                    },
                    "characters": chars,
                })
                dialogue_scenes.append(dialogue)

        return {"scene_plans": scene_plans, "dialogue_scenes": dialogue_scenes}

    return Pipeline("full", [
        Stage("parse", _stage_parse, skip_on_failure=True),
        Stage("narrative", _full_narrative, temperature=0.2, max_retries=2, skip_on_failure=True),
        Stage("characters", _full_characters, temperature=0.2, max_retries=2, skip_on_failure=True),
        Stage("world", _full_world, temperature=0.3, max_retries=1, skip_on_failure=True,
              default_output={"world_rules": [], "geography": []}),
        Stage("timeline", _full_timeline, temperature=0.2, max_retries=2, skip_on_failure=True),
        Stage("episode_plan", _full_episode_plan, temperature=0.3, max_retries=2, skip_on_failure=True),
        Stage("scenes_dialogue", _full_scenes_and_dialogue, temperature=0.4, max_retries=2, skip_on_failure=True),
        Stage("build_screenplay", _stage_build_screenplay, skip_on_failure=False),
        Stage("critic", _stage_critic, skip_on_failure=True,
              default_output={"violations": [], "score": 0.9}),
        Stage("validate_output", _stage_validate_output, skip_on_failure=True,
              default_output={"validation_report": {"passed": True, "errors": [], "warnings": [], "score": 1.0},
                               "violations": [], "critic_score": 1.0}),
    ])


# ── Public Entry Point ──

PIPELINE_REGISTRY = {
    "fast": build_fast_pipeline,
    "full": build_full_pipeline,
}


def run_pipeline(novel_text: str, novel_title: str = "", genre: str = "",
                 pipeline: str = "fast") -> PipelineState:
    """Run a full conversion pipeline. This is the main entry point."""
    state = build_state(novel_text, novel_title, genre, pipeline=pipeline)

    builder = PIPELINE_REGISTRY.get(pipeline, build_fast_pipeline)
    try:
        pipe = builder()
        state = pipe.run(state)
    except Exception as e:
        state.error = f"Pipeline error: {type(e).__name__}: {e}\n{traceback.format_exc()}"
        state.completed = False

    return state


def state_to_response(state: PipelineState) -> dict:
    """Convert PipelineState to API response dict."""
    yaml_output = state.screenplay_yaml
    if not yaml_output and isinstance(state.screenplay, dict):
        from backend.schemas.validator import screenplay_to_yaml
        try:
            from backend.schemas.models import Screenplay
            sp = Screenplay(**state.screenplay)
            yaml_output = screenplay_to_yaml(sp)
        except Exception:
            pass

    # Read from stage outputs (set via dynamic attributes)
    pre = getattr(state, "preprocess", {}) or {}
    if not isinstance(pre, dict):
        pre = {}
    bp = getattr(state, "batch_plan", {}) or {}
    if not isinstance(bp, dict):
        bp = {}

    episodes = bp.get("episodes", [])
    if not episodes and isinstance(state.screenplay, dict):
        episodes = state.screenplay.get("episodes", [])

    total_scenes = sum(len(ep.get("scenes", [])) for ep in episodes)

    chars = pre.get("characters", [])
    if not chars and isinstance(state.screenplay, dict):
        chars = state.screenplay.get("characters", [])

    return {
        "status": "completed" if state.completed else "error",
        "completed": state.completed,
        "error": state.error,
        "language": state.language,
        "pipeline": state.pipeline_name,
        "chapters_processed": state.num_chapters,
        "characters_extracted": len(chars),
        "episodes_planned": len(episodes),
        "scenes_written": total_scenes,
        "critic_score": state.critic_score,
        "violations": state.violations,
        "screenplay_yaml": yaml_output,
        "stage_results": {
            name: {"success": r.success, "attempts": r.attempts, "error": r.error}
            for name, r in state.stage_results.items()
        },
    }
