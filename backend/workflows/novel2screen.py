from __future__ import annotations

import logging
import uuid
from typing import Any

from backend.agents.character import CharacterAgent
from backend.agents.consistency import ConsistencyAgent
from backend.agents.critic import CriticAgent
from backend.agents.dialogue import DialogueAgent
from backend.agents.episode_planner import EpisodePlannerAgent
from backend.agents.narrative import NarrativeAgent
from backend.agents.repair import RepairAgent
from backend.agents.scene_planner import ScenePlannerAgent
from backend.agents.timeline import TimelineAgent
from backend.agents.world import WorldAgent
from backend.schemas.models import Screenplay
from backend.schemas.validator import screenplay_to_yaml, validate_screenplay_yaml, yaml_to_screenplay

logger = logging.getLogger(__name__)


class Novel2ScreenWorkflow:
    def __init__(self, config: Any, llm_client: Any, memory_manager: Any) -> None:
        self.config = config
        self.llm_client = llm_client
        self.memory_manager = memory_manager
        self._narrative = NarrativeAgent(llm_client, memory_manager)
        self._character = CharacterAgent(llm_client, memory_manager)
        self._world = WorldAgent(llm_client, memory_manager)
        self._timeline = TimelineAgent(llm_client, memory_manager)
        self._episode_planner = EpisodePlannerAgent(llm_client, memory_manager)
        self._scene_planner = ScenePlannerAgent(llm_client, memory_manager)
        self._dialogue = DialogueAgent(llm_client, memory_manager)
        self._critic = CriticAgent(llm_client, memory_manager)
        self._repair = RepairAgent(llm_client, memory_manager)
        self._consistency = ConsistencyAgent(llm_client, memory_manager)

    def parse_and_segment(self, text: str) -> list[str]:
        from backend.core.preprocessor import parse_chapters
        return parse_chapters(text)

    def _init_semantic_memory(self, novel_text: str) -> None:
        chunks = self.memory_manager.semantic.chunk_text(novel_text)
        if not chunks:
            return
        self.memory_manager.semantic.index(chunks)
        logger.info("Indexed %d chunks into semantic memory", len(chunks))

    def fast_run(self, novel_text: str, mode: str = "auto") -> dict[str, Any]:
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        logger.info("fast_run | task_id=%s", task_id)
        self._init_semantic_memory(novel_text)

        try:
            narrative = self._narrative.run({"chunks": [novel_text]})
            character_result = self._character.run({"chunks": [novel_text]})
            world_result = self._world.run({"chunks": [novel_text]})

            screenplay = self._build_screenplay({
                "narrative": narrative,
                "characters": character_result,
                "world": world_result,
                "episodes": [],
            })
            yaml_content = screenplay_to_yaml(screenplay)

            return {"task_id": task_id, "yaml_content": yaml_content, "status": "completed"}
        except Exception:
            logger.exception("fast_run | task_id=%s | failed", task_id)
            return {"task_id": task_id, "yaml_content": "", "status": "failed"}

    def run(self, novel_text: str, mode: str = "auto") -> dict[str, Any]:
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        logger.info("run | task_id=%s", task_id)
        self._init_semantic_memory(novel_text)

        try:
            narrative = self._narrative.retry({"chunks": [novel_text]})
            character_result = self._character.retry({"chunks": [novel_text]})
            world_result = self._world.run({"chunks": [novel_text]})
            timeline = self._timeline.run({"chunks": [novel_text], "mode": mode})

            ep_plan = self._episode_planner.run({
                "narrative": narrative,
                "characters": character_result,
                "mode": mode,
                "num_episodes": 4,
            })
            episodes_data = ep_plan.get("episodes", [])

            assembled: list[dict[str, Any]] = []
            for ep in episodes_data:
                ep_id = ep.get("id", "ep_001")
                scenes = self._scene_planner.run({
                    "episode_id": ep_id,
                    "summary": ep.get("summary", ""),
                    "characters": character_result.get("characters", []),
                })
                ep["scenes"] = scenes.get("scenes", [])
                assembled.append(ep)

            screenplay = self._build_screenplay({
                "narrative": narrative,
                "characters": character_result,
                "world": world_result,
                "episodes": assembled,
            })
            yaml_content = screenplay_to_yaml(screenplay)

            critic = self._critic.run({"yaml_content": yaml_content, "fast": False})
            violations = critic.get("violations", [])
            if violations:
                repair = self._repair.run({"yaml_content": yaml_content, "violations": violations})
                yaml_content = repair.get("repaired_yaml", yaml_content)

            return {"task_id": task_id, "yaml_content": yaml_content, "status": "completed"}
        except Exception:
            logger.exception("run | task_id=%s | failed", task_id)
            return {"task_id": task_id, "yaml_content": "", "status": "failed"}

    def _build_screenplay(self, data: dict[str, Any]) -> Screenplay:
        chars_raw = data.get("characters", [])
        if isinstance(chars_raw, dict):
            chars_raw = chars_raw.get("characters", [])
        if not isinstance(chars_raw, list):
            chars_raw = []

        from backend.schemas.models import Character, CharacterRole
        characters = [
            Character(
                id=c.get("id", f"char_{(i+1):03d}"),
                name=c.get("name", ""),
                role=CharacterRole(c.get("role", "supporting")),
                goal=c.get("goal", ""),
                fear=c.get("fear", ""),
                arc=c.get("arc", ""),
                voice_style=c.get("voice_style", ""),
            )
            for i, c in enumerate(chars_raw)
            if isinstance(c, dict)
        ]

        narrative = data.get("narrative", {})
        if isinstance(narrative, dict):
            title = narrative.get("title", narrative.get("theme", "Untitled"))
            theme = narrative.get("theme", "")
            major_events = narrative.get("major_events", [])
            logline = ". ".join(e.get("event", e.get("name", "")) for e in (major_events if isinstance(major_events, list) else [])[:3]) or "A story unfolds."
        else:
            title = "Untitled"
            theme = ""
            logline = ""

        world = data.get("world", {})
        genre = "drama"
        if isinstance(world, dict):
            rules = world.get("world_rules", world)
            if isinstance(rules, dict) and rules.get("magic"):
                genre = "fantasy"

        return Screenplay(
            title=title,
            logline=logline,
            genre=genre,
            theme=theme,
            characters=characters,
            episodes=[],
        )

    def run_consistency_check(self, original_chunks: list[str], edited_yaml: str) -> dict[str, Any]:
        return self._consistency.run({
            "original_chunks": original_chunks,
            "edited_yaml": edited_yaml,
        })

    def save_export(self, task_id: str, yaml_content: str) -> str:
        import os
        export_dir = "./data/exports"
        os.makedirs(export_dir, exist_ok=True)
        filepath = os.path.join(export_dir, f"{task_id}.yaml")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(yaml_content)
        return filepath

    def import_edits(self, task_id: str, edited_yaml: str) -> dict[str, Any]:
        validation = validate_screenplay_yaml(edited_yaml)

        if not validation.valid:
            original_chunks: list[str] = []
            repair_result = self._repair.run({
                "yaml_content": edited_yaml,
                "issues": [{"severity": "critical", "category": "validation", "description": e} for e in validation.errors],
                "suggestions": validation.warnings,
                "original_text": "",
            })

            if repair_result.get("repaired_yaml"):
                revalidated = validate_screenplay_yaml(repair_result["repaired_yaml"])
                return {
                    "task_id": task_id,
                    "status": "repaired" if revalidated.valid else "validation_failed",
                    "validated": revalidated.valid,
                    "repaired_yaml": repair_result.get("repaired_yaml", ""),
                    "changes": [c.get("field", "") for c in repair_result.get("changes_made", [])],
                }

        critic_result = self._critic.run({
            "yaml_content": edited_yaml,
            "original_text": "",
            "characters": [],
        })

        return {
            "task_id": task_id,
            "status": "validated",
            "validated": validation.valid,
            "critic_score": critic_result.get("score", 0),
            "repaired_yaml": edited_yaml,
            "changes": [],
        }
