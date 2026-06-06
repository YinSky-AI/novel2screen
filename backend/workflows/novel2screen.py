from __future__ import annotations
import logging, uuid
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
from backend.schemas.validator import screenplay_to_yaml, validate_screenplay_yaml

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

    def parse_and_segment(self, text: str) -> list[dict[str, str]]:
        from backend.core.preprocessor import parse_chapters
        return parse_chapters(text)

    def _init_semantic_memory(self, novel_text: str) -> None:
        try:
            from backend.core.preprocessor import chunk_paragraphs
            docs = chunk_paragraphs(novel_text, max_chars=500)
            if docs:
                self.memory_manager.semantic.index(docs)
                logger.info("RAG: indexed %d chunks", len(docs))
        except Exception as e:
            logger.warning("RAG index skipped: %s", e)

    def fast_run(self, novel_text: str, mode: str = "auto") -> dict[str, Any]:
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        self._init_semantic_memory(novel_text)
        try:
            narrative = self._narrative.retry({"novel_text": novel_text})
            character_result = self._character.retry({"novel_text": novel_text})

            # Build basic episodes from major_events
            chars_raw = character_result.get("characters", []) if isinstance(character_result, dict) else []
            episodes = []
            events = narrative.get("major_events", []) if isinstance(narrative, dict) else []
            if events:
                ep_scenes = []
                for i, ev in enumerate(events):
                    if not isinstance(ev, dict):
                        continue
                    ep_scenes.append({
                        "scene_id": f"sc_{(i+1):03d}",
                        "location": ev.get("location", "Unknown"),
                        "time": "Day",
                        "beats": [{
                            "type": "action",
                            "content": ev.get("event", ev.get("description", "")),
                            "emotion": None,
                        }],
                        "transition": "cut",
                        "duration_estimate": "45s",
                    })
                episodes.append({
                    "id": "ep_001",
                    "title": narrative.get("title", "Episode 1"),
                    "summary": narrative.get("logline", ""),
                    "scenes": ep_scenes,
                })

            screenplay = self._build_screenplay({
                "narrative": narrative,
                "characters": character_result,
                "world": {},
                "episodes": episodes,
            })
            yaml_content = screenplay_to_yaml(screenplay)
            self._fidelity_check(novel_text, character_result)
            return {"task_id": task_id, "yaml_content": yaml_content, "status": "completed"}
        except Exception:
            logger.exception("fast_run failed")
            return {"task_id": task_id, "yaml_content": "", "status": "failed"}

    def run(self, novel_text: str, mode: str = "auto") -> dict[str, Any]:
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        self._init_semantic_memory(novel_text)
        try:
            narrative = self._narrative.retry({"novel_text": novel_text})
            character_result = self._character.retry({"novel_text": novel_text})
            char_list = character_result.get("characters", []) if isinstance(character_result, dict) else []

            world_result = self._world.run({"novel_text": novel_text})
            _timeline = self._timeline.run({"novel_text": novel_text})

            ep_plan = self._episode_planner.run({"novel_text": novel_text, "characters": char_list})
            episodes_data = ep_plan.get("episodes", [])

            assembled: list[dict[str, Any]] = []
            for ep in episodes_data:
                if not isinstance(ep, dict):
                    continue
                scenes_result = self._scene_planner.run({
                    "episode_id": ep.get("id", "ep_001"),
                    "summary": ep.get("summary", ""),
                    "characters": char_list,
                })
                scenes_list = scenes_result.get("scenes", []) if isinstance(scenes_result, dict) else []

                scenes_with_dialogue = []
                for sc in scenes_list:
                    if not isinstance(sc, dict):
                        continue
                    dialogue_result = self._dialogue.run({
                        "scene": sc,
                        "characters": char_list,
                    })
                    beats = dialogue_result.get("beats", []) if isinstance(dialogue_result, dict) else []
                    sc["beats"] = beats if beats else [{"type": "action", "content": sc.get("objective", "Scene"), "emotion": None}]
                    scenes_with_dialogue.append(sc)

                ep["scenes"] = scenes_with_dialogue
                assembled.append(ep)

            screenplay = self._build_screenplay({
                "narrative": narrative,
                "characters": character_result,
                "world": world_result,
                "episodes": assembled,
            })
            yaml_content = screenplay_to_yaml(screenplay)

            critic = self._critic.run({"yaml_content": yaml_content})
            violations = critic.get("violations", [])
            if violations:
                repair = self._repair.run({"yaml_content": yaml_content, "violations": violations})
                yaml_content = repair.get("repaired_yaml", yaml_content)

            self._fidelity_check(novel_text, character_result)
            return {"task_id": task_id, "yaml_content": yaml_content, "status": "completed"}
        except Exception:
            logger.exception("run failed")
            return {"task_id": task_id, "yaml_content": "", "status": "failed"}

    def _fidelity_check(self, novel_text: str, character_result: dict) -> None:
        try:
            from backend.core.preprocessor import extract_named_entities
            src_entities = extract_named_entities(novel_text[:5000])
            yaml_chars = set()
            chars_data = character_result.get("characters", []) if isinstance(character_result, dict) else []
            for c in chars_data:
                if isinstance(c, dict):
                    name = c.get("name", "")
                    if name:
                        yaml_chars.add(name)
            src_chars = set(src_entities.get("characters", []))
            fabricated = yaml_chars - src_chars
            if fabricated:
                logger.warning("Potential fabricated characters: %s", fabricated)
        except Exception:
            pass

    def _build_screenplay(self, data: dict) -> Screenplay:
        narrative = data.get("narrative", {})
        if not isinstance(narrative, dict):
            narrative = {}

        title = narrative.get("title", "Untitled")
        logline = narrative.get("logline", "")
        theme = narrative.get("theme", "")
        genre = narrative.get("genre", "drama")

        chars = data.get("characters", [])
        if isinstance(chars, dict):
            chars = chars.get("characters", [])
        if not isinstance(chars, list):
            chars = []

        from backend.schemas.models import Character, CharacterRole

        characters = []
        for i, c in enumerate(chars):
            if not isinstance(c, dict):
                continue
            role = c.get("role", "supporting")
            try:
                role_enum = CharacterRole(role)
            except ValueError:
                role_enum = CharacterRole.SUPPORTING
            characters.append(Character(
                id=c.get("id", f"char_{(i+1):03d}"),
                name=c.get("name", ""),
                role=role_enum,
                goal=c.get("goal", ""),
                fear=c.get("fear", ""),
                arc=c.get("arc", ""),
                voice_style=c.get("voice_style", ""),
            ))

        eps = data.get("episodes", [])
        if isinstance(eps, dict):
            eps = eps.get("episodes", [])
        if not isinstance(eps, list):
            eps = []

        if not eps and narrative.get("major_events"):
            eps = [{"id": "ep_001", "title": title, "summary": logline, "scenes": []}]

        from backend.schemas.models import Episode, Scene, Beat, BeatType, Transition

        episodes = []
        for ep in eps:
            if not isinstance(ep, dict):
                continue
            scenes_raw = ep.get("scenes", [])
            if isinstance(scenes_raw, dict):
                scenes_raw = scenes_raw.get("scenes", [])
            if not isinstance(scenes_raw, list):
                scenes_raw = []
            scenes = []
            for sc in scenes_raw:
                if not isinstance(sc, dict):
                    continue
                beats_raw = sc.get("beats", [])
                if not isinstance(beats_raw, list):
                    beats_raw = []
                beats = []
                for b in beats_raw:
                    if not isinstance(b, dict):
                        beats_raw = []
                        break
                    try:
                        bt = BeatType(b.get("type", "action"))
                    except ValueError:
                        bt = BeatType.ACTION
                    beats.append(Beat(type=bt, character_id=b.get("character_id"), content=b.get("content", ""), emotion=b.get("emotion")))
                if not beats and data.get("characters"):
                    beats = [Beat(type=BeatType.ACTION, content=f"Scene at {sc.get('location', 'unknown')}", emotion=None)]
                try:
                    tr = Transition(sc.get("transition", "cut"))
                except ValueError:
                    tr = Transition.CUT
                scenes.append(Scene(
                    scene_id=sc.get("scene_id", f"sc_{(len(scenes)+1):03d}"),
                    location=sc.get("location", ""),
                    time=sc.get("time", ""),
                    beats=beats,
                    transition=tr,
                    duration_estimate=sc.get("duration_estimate", "30s"),
                ))
            episodes.append(Episode(
                id=ep.get("id", f"ep_{(len(episodes)+1):03d}"),
                title=ep.get("title", ""),
                summary=ep.get("summary", ""),
                scenes=scenes,
            ))

        return Screenplay(title=title, logline=logline, genre=genre, theme=theme, characters=characters, episodes=episodes)

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
