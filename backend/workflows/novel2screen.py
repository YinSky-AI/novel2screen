from __future__ import annotations

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
from backend.core.memory import MemoryManager
from backend.core.preprocessor import smart_chunk
from backend.harness.novel_reader import NovelReader
from backend.harness.orchestrator import PipelineOrchestrator, PipelineState, build_fast_pipeline, build_full_pipeline, state_to_response
from backend.schemas.models import ConvertResponse, ConvertRequest, Screenplay, TaskStatus
from backend.schemas.validator import screenplay_to_yaml, validate_screenplay_yaml, yaml_to_screenplay


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

    def parse_and_segment(self, text: str) -> list[dict[str, str | int]]:
        reader = NovelReader(text)
        return reader.get_chapters()

    def _init_semantic_memory(self, novel_text: str) -> None:
        chunks = self.memory_manager.semantic.chunk_text(novel_text)
        if not chunks:
            return
        self.memory_manager.semantic.index(chunks)
        logger.info("Indexed %d chunks into semantic memory", len(chunks))

    def fast_run(self, novel_text: str, mode: str = "auto") -> ConvertResponse:
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        self._init_semantic_memory(novel_text)

        state = PipelineState(
            novel_text=novel_text,
            language=NovelReader(novel_text).language,
            chunks=smart_chunk(novel_text),
            progress=0.0,
        )

        agents = {
            "narrative": self._narrative,
            "character": self._character,
            "world": self._world,
            "timeline": self._timeline,
            "episode_planner": self._episode_planner,
            "scene_planner": self._scene_planner,
            "critic": self._critic,
            "repair": self._repair,
            "consistency": self._consistency,
        }

        orchestrator = PipelineOrchestrator(agents)
        state = build_fast_pipeline(orchestrator, state)

        if state.screenplay:
            state.yaml_content = screenplay_to_yaml(state.screenplay)

        return state_to_response(state, task_id)

    def run(self, novel_text: str, mode: str = "auto") -> ConvertResponse:
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        self._init_semantic_memory(novel_text)

        state = PipelineState(
            novel_text=novel_text,
            language=NovelReader(novel_text).language,
            chunks=smart_chunk(novel_text),
            progress=0.0,
        )

        agents = {
            "narrative": self._narrative,
            "character": self._character,
            "world": self._world,
            "timeline": self._timeline,
            "episode_planner": self._episode_planner,
            "scene_planner": self._scene_planner,
            "critic": self._critic,
            "repair": self._repair,
            "consistency": self._consistency,
        }

        orchestrator = PipelineOrchestrator(agents)
        state = build_full_pipeline(orchestrator, state)

        if state.screenplay and not state.yaml_content:
            state.yaml_content = screenplay_to_yaml(state.screenplay)

        return state_to_response(state, task_id)

    def _build_screenplay(self, data: dict[str, Any]) -> Screenplay:
        if "characters" in data:
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
                for i, c in enumerate(data.get("characters", []))
            ]
        else:
            characters = []

        return Screenplay(
            title=data.get("title", "Untitled"),
            logline=data.get("logline", ""),
            genre=data.get("genre", ""),
            theme=data.get("theme", ""),
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
