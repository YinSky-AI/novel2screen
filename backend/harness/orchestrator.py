from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from backend.schemas.models import ConvertResponse, Screenplay


@dataclass
class PipelineState:
    novel_text: str = ""
    chapters: list[dict[str, str | int]] = field(default_factory=list)
    language: str = "en"
    chunks: list[str] = field(default_factory=list)
    narrative: dict[str, Any] = field(default_factory=dict)
    characters: dict[str, Any] = field(default_factory=dict)
    world: dict[str, Any] = field(default_factory=dict)
    timeline: dict[str, Any] = field(default_factory=dict)
    episodes_plan: dict[str, Any] = field(default_factory=dict)
    scenes: list[dict[str, Any]] = field(default_factory=list)
    screenplay: Screenplay | None = None
    critic: dict[str, Any] = field(default_factory=dict)
    repair: dict[str, Any] = field(default_factory=dict)
    consistency: dict[str, Any] = field(default_factory=dict)
    yaml_content: str = ""
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    current_stage: str = ""
    progress: float = 0.0


class PipelineOrchestrator:
    def __init__(self, agents: dict[str, Any]) -> None:
        self.agents = agents

    def execute_step(self, agent_name: str, input_data: dict[str, Any], state: PipelineState) -> dict[str, Any]:
        agent = self.agents.get(agent_name)
        if agent is None:
            state.errors.append(f"Agent {agent_name} not found")
            return {}
        try:
            result = agent.run(input_data)
            if not agent.validate(result):
                errors = agent.validate_with_errors(result)
                state.warnings.extend(errors)
                state.warnings.append(f"Agent {agent_name} validation failed, retrying...")
                result = agent.retry(input_data, max_attempts=2)
                if not agent.validate(result):
                    state.errors.append(f"Agent {agent_name} failed after retries")
            return result
        except Exception as e:
            state.errors.append(f"Agent {agent_name} error: {e}")
            return {}


def build_fast_pipeline(orchestrator: PipelineOrchestrator, state: PipelineState) -> PipelineState:
    state.current_stage = "Narrative extraction"
    state.progress = 10.0
    state.narrative = orchestrator.execute_step(
        "narrative", {"novel_text": state.novel_text}, state
    )

    state.current_stage = "Character extraction"
    state.progress = 30.0
    state.characters = orchestrator.execute_step(
        "character", {"novel_text": state.novel_text, "language": state.language}, state
    )

    state.current_stage = "World building"
    state.progress = 50.0
    state.world = orchestrator.execute_step(
        "world", {"novel_text": state.novel_text}, state
    )

    state.current_stage = "Episode planning"
    state.progress = 70.0
    timeline = orchestrator.execute_step(
        "timeline", {"novel_text": state.novel_text, "characters": state.characters.get("characters", []), "narrative": state.narrative}, state
    )
    state.timeline = timeline

    episodes_plan = orchestrator.execute_step(
        "episode_planner", {
            "novel_text": state.novel_text,
            "timeline": timeline,
            "narrative": state.narrative,
            "target_episodes": 6,
        }, state
    )
    state.episodes_plan = episodes_plan

    scenes_list: list[dict[str, Any]] = []
    episodes = episodes_plan.get("episodes", [])
    total_eps = len(episodes)
    for i, ep in enumerate(episodes):
        state.current_stage = f"Scene planning: {ep.get('title', f'Episode {i+1}')}"
        state.progress = 70.0 + (20.0 * (i + 1) / max(total_eps, 1))
        scene_data = orchestrator.execute_step(
            "scene_planner", {
                "novel_text": state.novel_text,
                "episodes": episodes,
                "characters": state.characters.get("characters", []),
                "world": state.world,
                "current_episode_id": ep.get("id", f"ep_{i+1:03d}"),
            }, state
        )
        scenes_list.append(scene_data)

    state.scenes = scenes_list
    state.current_stage = "Building screenplay"
    state.progress = 95.0
    state.screenplay = _normalize_episodes(state)

    state.current_stage = "Complete"
    state.progress = 100.0
    return state


def build_full_pipeline(orchestrator: PipelineOrchestrator, state: PipelineState) -> PipelineState:
    state = build_fast_pipeline(orchestrator, state)

    screenplay_yaml = ""
    if state.screenplay:
        from backend.schemas.validator import screenplay_to_yaml
        screenplay_yaml = screenplay_to_yaml(state.screenplay)

    state.current_stage = "Quality review"
    state.progress = 95.0
    critic_result = orchestrator.execute_step(
        "critic", {
            "yaml_content": screenplay_yaml,
            "original_text": state.novel_text,
            "characters": state.characters.get("characters", []),
        }, state
    )
    state.critic = critic_result

    if critic_result.get("score", 10) < 6:
        state.current_stage = "Auto-repair"
        repair_result = orchestrator.execute_step(
            "repair", {
                "yaml_content": screenplay_yaml,
                "issues": critic_result.get("issues", []),
                "suggestions": critic_result.get("suggestions", []),
                "original_text": state.novel_text,
            }, state
        )
        state.repair = repair_result
        if repair_result.get("repaired_yaml"):
            from backend.schemas.validator import yaml_to_screenplay
            try:
                state.screenplay = yaml_to_screenplay(repair_result["repaired_yaml"])
                state.yaml_content = repair_result["repaired_yaml"]
            except Exception:
                pass

    state.current_stage = "Consistency check"
    state.progress = 98.0
    consistency_result = orchestrator.execute_step(
        "consistency", {
            "original_chunks": state.chunks,
            "edited_yaml": state.yaml_content or screenplay_yaml,
            "original_text": state.novel_text,
        }, state
    )
    state.consistency = consistency_result

    state.current_stage = "Complete"
    state.progress = 100.0
    return state


def _normalize_episodes(state: PipelineState) -> Screenplay | None:
    from backend.schemas.models import Beat, BeatType, Character, CharacterRole, Episode, Scene, Screenplay, Transition

    characters = [
        Character(
            id=c.get("id", f"char_{(i+1):03d}"),
            name=c.get("name", f"Unknown_{i}"),
            role=CharacterRole(c.get("role", "supporting")),
            goal=c.get("goal", ""),
            fear=c.get("fear", ""),
            arc=c.get("arc", ""),
            voice_style=c.get("voice_style", ""),
        )
        for i, c in enumerate(state.characters.get("characters", []))
    ]

    episodes_list: list[Episode] = []
    episode_plans = state.episodes_plan.get("episodes", [])
    for ep_idx, ep_plan in enumerate(episode_plans):
        ep_id = ep_plan.get("id", f"ep_{(ep_idx + 1):03d}")

        ep_scenes_data = next(
            (s for s in state.scenes if s.get("episode_id") == ep_id),
            state.scenes[ep_idx] if ep_idx < len(state.scenes) else {},
        )

        scenes_list: list[Scene] = []
        for sc_idx, sc_data in enumerate(ep_scenes_data.get("scenes", [])):
            beats = [
                Beat(
                    type=BeatType(b.get("type", "action")),
                    character_id=b.get("character_id"),
                    content=b.get("content", ""),
                    emotion=b.get("emotion"),
                )
                for b in sc_data.get("beats", [])
            ]
            scenes_list.append(
                Scene(
                    scene_id=sc_data.get("scene_id", f"sc_{(sc_idx + 1):03d}"),
                    location=sc_data.get("location", ""),
                    time=sc_data.get("time", ""),
                    visual_focus=sc_data.get("visual_focus"),
                    sound_effect=sc_data.get("sound_effect"),
                    voice_over=sc_data.get("voice_over"),
                    beats=beats,
                    transition=Transition(sc_data.get("transition", "cut")),
                    duration_estimate=sc_data.get("duration_estimate", "60s"),
                )
            )

        episodes_list.append(
            Episode(
                id=ep_id,
                title=ep_plan.get("title", f"Episode {ep_idx + 1}"),
                summary=ep_plan.get("summary", ""),
                scenes=scenes_list,
            )
        )

    return Screenplay(
        title=state.narrative.get("title", "Untitled"),
        logline=state.narrative.get("logline", ""),
        genre=state.narrative.get("genre", ""),
        theme=state.narrative.get("theme", ""),
        characters=characters,
        episodes=episodes_list,
    )


def state_to_response(state: PipelineState, task_id: str) -> ConvertResponse:
    yaml_content = state.yaml_content
    if not yaml_content and state.screenplay:
        from backend.schemas.validator import screenplay_to_yaml
        yaml_content = screenplay_to_yaml(state.screenplay)

    status = "error" if state.errors else "completed"
    return ConvertResponse(
        task_id=task_id,
        status=status,
        message="; ".join(state.errors) if state.errors else "Pipeline completed successfully",
        yaml_content=yaml_content,
        screenplay=state.screenplay,
    )
