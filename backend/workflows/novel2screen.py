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
            chars_raw = character_result.get("characters", []) if isinstance(character_result, dict) else []

            # Step 3: LLM writes actual scenes with dialogue beats
            events = narrative.get("major_events", []) if isinstance(narrative, dict) else []
            ep_scenes = self._llm_write_scenes(novel_text, events, chars_raw)

            episodes = [{
                "id": "ep_001",
                "title": narrative.get("title", "Episode 1") if isinstance(narrative, dict) else "Episode 1",
                "summary": narrative.get("logline", "") if isinstance(narrative, dict) else "",
                "scenes": ep_scenes,
            }]

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

    def _llm_write_scenes(self, novel_text: str, events: list, characters: list) -> list[dict]:
        """Have LLM write proper screenplay scenes from narrative events."""
        import json as _json
        events_str = _json.dumps(events[:10], ensure_ascii=False)
        chars_str = _json.dumps([{"id": c.get("id", ""), "name": c.get("name", "")} for c in characters[:10] if isinstance(c, dict)], ensure_ascii=False)

        prompt = f"""Write complete screenplay scenes based on these events and characters.
For EACH event, write a vivid scene with:
- scene_id: "sc_001", "sc_002", etc.
- location: EXACT specific location from the text (NEVER "Unknown")
- time: specific time like "Night", "Dawn", "Midnight", "Afternoon" (NEVER just "Day")
- visual_focus: what the camera focuses on
- sound_effect: ambient or specific sounds
- transition: varied — use "cut", "fade", "dissolve", "wipe" appropriately
- duration_estimate: match scene complexity — "30s", "60s", "120s", "180s"
- beats: at least 3 beats per scene, mixing dialogue/action/reaction types
  - Each dialogue beat MUST have a character_id matching the characters list
  - Each beat MUST have an emotion (e.g. "tension", "fear", "anger", "hope", "sadness", "joy", "neutral")
  - Write specific, vivid beat content — not generic summaries

Events: {events_str}
Characters: {chars_str}
Original text excerpt (for reference): {novel_text[:2000]}

Output ONLY valid JSON: {{"scenes": [...]}} No markdown, no explanation."""

        try:
            response = self._narrative._call_llm(prompt, system_prompt="You are a professional screenwriter. Write specific, cinematic scenes using exact details from the source text. Never use generic values like 'Unknown' or 'Day'. Output valid JSON only.")
            result = self._narrative._parse_json(response)
            scenes = result.get("scenes", [])
            if scenes and isinstance(scenes, list):
                return scenes
        except Exception as e:
            logger.warning("LLM scene generation failed: %s, using fallback", e)

        # Ultimate fallback
        fallback = []
        for i, ev in enumerate(events):
            if not isinstance(ev, dict):
                continue
            fallback.append({
                "scene_id": f"sc_{(i+1):03d}",
                "location": str(ev.get("location", "Unknown")),
                "time": str(ev.get("time", "Day")),
                "visual_focus": str(ev.get("visual_focus", "")),
                "sound_effect": str(ev.get("sound_effect", "")),
                "transition": "cut",
                "duration_estimate": "90s",
                "beats": [
                    {"type": "action", "content": str(ev.get("event", "Scene")), "character_id": None, "emotion": str(ev.get("emotion", "neutral"))},
                    {"type": "dialogue", "content": "...", "character_id": (characters[0].get("id", "") if characters else ""), "emotion": str(ev.get("emotion", "neutral"))},
                    {"type": "reaction", "content": "...", "character_id": None, "emotion": str(ev.get("emotion", "neutral"))},
                ],
            })
        if not fallback:
            fallback = [{"scene_id": "sc_001", "location": "Unknown", "time": "Day", "transition": "cut", "duration_estimate": "60s", "beats": [{"type": "action", "content": "Scene", "emotion": "neutral"}]}]
        return fallback

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
            if not isinstance(scenes_raw, list) or len(scenes_raw) == 0:
                scenes_raw = [{
                    "scene_id": "sc_001",
                    "location": "Unknown",
                    "time": "Day",
                    "transition": "cut",
                    "duration_estimate": "60s",
                    "beats": [{"type": "action", "content": ep.get("summary", "Scene")}],
                }]

            scenes = []
            for sc in scenes_raw:
                if not isinstance(sc, dict):
                    continue
                beats_raw = sc.get("beats", [])
                if not isinstance(beats_raw, list):
                    beats_raw = []
                if len(beats_raw) == 0:
                    beats_raw = [{"type": "action", "content": sc.get("objective", sc.get("summary", "Scene")), "emotion": None}]
                beats = []
                for b in beats_raw:
                    if not isinstance(b, dict):
                        continue
                    try:
                        bt = BeatType(b.get("type", "action"))
                    except ValueError:
                        bt = BeatType.ACTION
                    beats.append(Beat(
                        type=bt,
                        character_id=b.get("character_id"),
                        content=b.get("content", ""),
                        emotion=b.get("emotion"),
                    ))
                if not beats:
                    beats = [Beat(type=BeatType.ACTION, content=f"Scene at {sc.get('location', 'unknown')}", emotion=None)]

                try:
                    tr = Transition(sc.get("transition", "cut"))
                except ValueError:
                    tr = Transition.CUT

                scenes.append(Scene(
                    scene_id=str(sc.get("scene_id", f"sc_{(len(scenes)+1):03d}")),
                    location=str(sc.get("location", "Unknown")),
                    time=str(sc.get("time", "Day")),
                    visual_focus=sc.get("visual_focus"),
                    sound_effect=sc.get("sound_effect"),
                    voice_over=sc.get("voice_over"),
                    beats=beats,
                    transition=tr,
                    duration_estimate=str(sc.get("duration_estimate", "60s")),
                ))

            episodes.append(Episode(
                id=str(ep.get("id", f"ep_{(len(episodes)+1):03d}")),
                title=str(ep.get("title", "")),
                summary=str(ep.get("summary", "")),
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
