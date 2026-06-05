"""Novel2Screen Workflow Orchestrator.
Supports two pipelines:
  - fast_run: 2-3 LLM calls with RAG (recommended for production)
  - run: 9+ agent sequential chain (for maximum quality, long novels).
"""
import contextlib
import json
import os
import re
from typing import Literal, TypedDict

import yaml

from backend.agents.character import CharacterAgent
from backend.agents.consistency import BidirectionalConsistencyAgent
from backend.agents.critic import CriticAgent
from backend.agents.dialogue import DialogueAgent
from backend.agents.episode_planner import EpisodePlannerAgent
from backend.agents.narrative import NarrativeAgent
from backend.agents.repair import RepairAgent
from backend.agents.scene_planner import ScenePlannerAgent
from backend.agents.timeline import TimelineAgent
from backend.agents.world import WorldAgent
from backend.config import CHROMA_PERSIST_DIR, CHUNK_OVERLAP, CHUNK_SIZE, EMBEDDING_MODEL, RAG_ENABLED
from backend.core.llm import llm_client
from backend.core.memory import CharacterBible, SemanticMemory, ShortTermMemory, WorldBible
from backend.core.preprocessor import batch_plan_episodes, preprocess_novel
from backend.core.prompts import FAST_CRITIC_SYSTEM, FAST_CRITIC_USER


class WorkflowState(TypedDict):
    novel_title: str
    novel_chunks: list[str]
    mode: Literal["short", "long"]
    genre: str
    pipeline: Literal["fast", "full"]

    narrative: dict
    characters: dict
    world: dict
    timeline: dict
    episode_plan: dict
    scene_plans: list[dict]
    dialogue_scenes: list[dict]

    screenplay_yaml: str
    screenplay: dict

    violations: list[dict]
    critic_score: float
    repair_changes: list[str]

    error: str
    completed: bool


def route_mode(num_chapters: int) -> str:
    return "short" if 3 <= num_chapters <= 10 else "long"


def parse_and_segment(novel_text: str, chunk_size: int = 3000) -> list[str]:
    chapters = re.split(
        r"(?:^|\n)(?:#+\s*)?(?:第[一二三四五六七八九十百千万零\d]+章|Chapter\s+\d+|[Cc]hapter\s+\d+)\s*[：:\s]*",
        novel_text, flags=re.MULTILINE,
    )
    chapters = [c.strip() for c in chapters if c.strip()]
    if len(chapters) <= 1:
        chunks = []
        paragraphs = novel_text.split("\n\n")
        current = ""
        for p in paragraphs:
            if len(current) + len(p) < chunk_size:
                current += "\n\n" + p
            else:
                if current:
                    chunks.append(current)
                current = p
        if current:
            chunks.append(current)
        return chunks[:100]
    return chapters


class Novel2ScreenWorkflow:
    """Orchestrates novel-to-screenplay conversion with dual pipeline support."""

    def __init__(self):
        self.narrative_agent = NarrativeAgent()
        self.character_agent = CharacterAgent()
        self.world_agent = WorldAgent()
        self.timeline_agent = TimelineAgent()
        self.episode_planner = EpisodePlannerAgent()
        self.scene_planner = ScenePlannerAgent()
        self.dialogue_agent = DialogueAgent()
        self.critic_agent = CriticAgent()
        self.repair_agent = RepairAgent()
        self.consistency_agent = BidirectionalConsistencyAgent()

        self.stm = ShortTermMemory()
        self.char_bible = CharacterBible()
        self.world_bible = WorldBible()

    def _init_semantic_memory(self, force: bool = False) -> SemanticMemory:
        return SemanticMemory(
            chunk_size=CHUNK_SIZE,
            overlap=CHUNK_OVERLAP,
            persist_dir=CHROMA_PERSIST_DIR,
            embedding_model=EMBEDDING_MODEL,
        )

    def _build_screenplay(self, novel_title: str, genre: str, pre: dict, raw_episodes: list[dict]) -> tuple[dict, str]:
        from backend.schemas.models import Screenplay
        from backend.schemas.validator import screenplay_to_yaml

        std_emos = {"anger", "fear", "joy", "sadness", "surprise", "disgust", "anticipation", "calm", "tension", "confusion", "resolve"}
        emo_map = {"震惊": "surprise", "愤怒": "anger", "恐惧": "fear", "悲伤": "sadness", "喜悦": "joy",
                   "怀疑": "tension", "专注": "calm", "紧张": "tension", "决心": "resolve", "困惑": "confusion",
                   "determined": "resolve", "desperation": "fear", "urgency": "tension", "suspicion": "tension", "determination": "resolve"}

        for ep in raw_episodes:
            ep.setdefault("scenes", [])
            for sc in ep.get("scenes", []):
                if not sc.get("characters_present"):
                    cids = list({b.get("character_id") for b in sc.get("beats", []) if b.get("character_id")})
                    if cids:
                        sc["characters_present"] = cids
                for b in sc.get("beats", []):
                    e = b.get("emotion")
                    if e:
                        k = e.lower().strip()
                        if k in std_emos:
                            b["emotion"] = k
                        elif k in emo_map:
                            b["emotion"] = emo_map[k]

        screenplay = Screenplay(
            title=novel_title,
            logline=pre.get("theme", ""),
            genre=genre,
            theme=pre.get("theme", ""),
            characters=pre.get("characters", []),
            episodes=raw_episodes,
        )
        screenplay_dict = screenplay.model_dump(exclude_none=True)
        raw_yaml = screenplay_to_yaml(screenplay)
        raw_yaml = re.sub(r"^`(?:yaml)?\s*", "", raw_yaml)
        raw_yaml = re.sub(r"\s*`$", "", raw_yaml)
        return screenplay_dict, raw_yaml

    def fast_run(self, novel_text: str, novel_title: str = "Untitled",
                 genre: str = "Drama", mode: str = "") -> dict:
        """Optimized pipeline: 2-3 LLM calls with RAG support."""
        state = {
            "novel_title": novel_title, "novel_chunks": [], "mode": mode or "short",
            "genre": genre, "pipeline": "fast",
            "narrative": {}, "characters": {}, "world": {}, "timeline": {},
            "episode_plan": {}, "scene_plans": [], "dialogue_scenes": [],
            "screenplay_yaml": "", "screenplay": {}, "violations": [],
            "critic_score": 1.0, "repair_changes": [], "error": "", "completed": False,
        }

        try:
            chunks = parse_and_segment(novel_text)
            state["novel_chunks"] = chunks
            if state["mode"] == "":
                state["mode"] = route_mode(len(chunks))

            sem_mem = self._init_semantic_memory()
            if RAG_ENABLED:
                with contextlib.suppress(Exception):
                    sem_mem.index(novel_text, source_label="novel")

            pre = preprocess_novel(chunks, semantic_memory=sem_mem, mode=state["mode"])
            state["narrative"] = {"theme": pre["theme"], "major_events": pre["major_events"], "turning_points": pre["turning_points"]}
            state["characters"] = {"characters": pre["characters"]}
            state["world"] = {"geography": pre.get("locations", [])}

            for char in pre.get("characters", []):
                self.char_bible.add_or_update(char)

            plan = batch_plan_episodes(pre, state["mode"], semantic_memory=sem_mem)
            state["episode_plan"] = {"episodes": plan.get("episodes", [])}

            raw_episodes = plan.get("episodes", [])
            if not raw_episodes:
                raw_episodes = [{"id": "ep_001", "title": novel_title or "Adaptation", "summary": "Auto-generated",
                    "scenes": [{"scene_id": "sc_001", "location": "Main", "time": "Unknown",
                        "beats": [{"type": "action", "content": "Opening."}],
                        "transition": "cut", "duration_estimate": "60s"}]}]

            state["screenplay"], state["screenplay_yaml"] = self._build_screenplay(
                novel_title, genre, pre, raw_episodes,
            )

            try:
                summary_data = {
                    "title": novel_title,
                    "episodes": len(plan.get("episodes", [])),
                    "scenes": sum(len(ep.get("scenes", [])) for ep in plan.get("episodes", [])),
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
                critic_data = json.loads(critic_text)
                state["violations"] = critic_data.get("violations", [])
                state["critic_score"] = critic_data.get("score", 1.0)
            except Exception:
                state["critic_score"] = 0.9

            if state["critic_score"] < 0.7:
                try:
                    ro = self.repair_agent.retry({"violations": state["violations"], "screenplay": state["screenplay_yaml"]})
                    ry = ro.get("yaml_output", "")
                    ry = re.sub(r"^`(?:yaml)?\s*", "", ry)
                    ry = re.sub(r"\s*`$", "", ry)
                    if ry:
                        state["screenplay_yaml"] = ry
                        state["repair_changes"].append("Quality repair applied")
                except Exception:
                    pass

            state["completed"] = True

        except Exception as e:
            state["error"] = str(e)
            import traceback
            state["error"] += "\n" + traceback.format_exc()

        return state

    def run(self, novel_text: str, novel_title: str = "Untitled",
            genre: str = "Drama", mode: str = "") -> dict:
        """Full agent chain: 9+ agents for maximum quality (long novels)."""
        state: WorkflowState = {
            "novel_title": novel_title, "novel_chunks": [], "mode": mode or "short",
            "genre": genre, "pipeline": "full",
            "narrative": {}, "characters": {}, "world": {}, "timeline": {},
            "episode_plan": {}, "scene_plans": [], "dialogue_scenes": [],
            "screenplay_yaml": "", "screenplay": {},
            "violations": [], "critic_score": 1.0, "repair_changes": [],
            "error": "", "completed": False,
        }

        try:
            chunks = parse_and_segment(novel_text)
            state["novel_chunks"] = chunks
            num_chapters = len(chunks)
            if state["mode"] == "":
                state["mode"] = route_mode(num_chapters)

            sem_mem = self._init_semantic_memory()
            if RAG_ENABLED:
                with contextlib.suppress(Exception):
                    sem_mem.index(novel_text, source_label="novel")

            self.stm.set_active_chapter("\n\n".join(chunks[:3]))

            state["narrative"] = self.narrative_agent.retry({"chunks": chunks})

            state["characters"] = self.character_agent.retry({"content": novel_text[:8000]})
            for char in state["characters"].get("characters", []):
                self.char_bible.add_or_update(char)

            if state["mode"] == "long":
                state["world"] = self.world_agent.retry({"content": novel_text[:8000]})
                self.world_bible.set_rules(state["world"].get("world_rules", []))
                self.world_bible.set_geography(state["world"].get("geography", []))
            else:
                state["world"] = {"world_rules": [], "geography": []}

            state["timeline"] = self.timeline_agent.retry({
                "major_events": state["narrative"].get("major_events", []),
                "mode": state["mode"],
            })

            state["episode_plan"] = self.episode_planner.retry({
                "narrative": state["narrative"],
                "characters": state["characters"].get("characters", []),
                "mode": state["mode"],
            })

            state["scene_plans"] = []
            state["dialogue_scenes"] = []
            episodes = state["episode_plan"].get("episodes", [])

            for ep in episodes:
                ep_id = ep.get("id", "ep_001")
                scene_plan = self.scene_planner.retry({
                    "episode_id": ep_id,
                    "episode_title": ep.get("title", ""),
                    "episode_summary": ep.get("summary", ""),
                    "characters": state["characters"].get("characters", []),
                    "world_context": state["world"],
                })
                state["scene_plans"].append(scene_plan)

                for sc_idx, sc_plan in enumerate(scene_plan.get("scenes", [])):
                    sc_input = {
                        "scene_id": sc_plan.get("scene_id", f"sc_{sc_idx+1:03d}"),
                        "location": sc_plan.get("location", "Unknown"),
                        "time": sc_plan.get("time", "Unknown"),
                    }
                    dialogue = self.dialogue_agent.retry({
                        "scene_plan": sc_input,
                        "characters": state["characters"].get("characters", []),
                    })
                    state["dialogue_scenes"].append(dialogue)

            dialogue_idx = 0
            episode_objects = []
            for ep_idx, ep in enumerate(episodes):
                # Use scene_plans to determine scene count per episode
                sp = state["scene_plans"][ep_idx] if ep_idx < len(state["scene_plans"]) else {}
                num_scenes = len(sp.get("scenes", []))
                if num_scenes > 0:
                    ep_scenes = state["dialogue_scenes"][dialogue_idx:dialogue_idx + num_scenes]
                    dialogue_idx += len(ep_scenes)
                elif state["dialogue_scenes"]:
                    # Fallback: distribute remaining scenes evenly
                    remaining = len(state["dialogue_scenes"]) - dialogue_idx
                    remaining_eps = len(episodes) - ep_idx
                    scenes_per_ep = max(1, remaining // max(remaining_eps, 1))
                    ep_scenes = state["dialogue_scenes"][dialogue_idx:dialogue_idx + scenes_per_ep]
                    dialogue_idx += len(ep_scenes)
                else:
                    ep_scenes = []
                episode_objects.append({
                    "id": ep["id"], "title": ep["title"], "summary": ep["summary"],
                    "scenes": ep_scenes,
                })



            from backend.schemas.models import Screenplay
            from backend.schemas.validator import screenplay_to_yaml

            screenplay = Screenplay(
                title=state["novel_title"],
                logline=state["narrative"].get("theme", ""),
                genre=state["genre"],
                theme=state["narrative"].get("theme", ""),
                characters=[self.char_bible.get(c.get("id", "")) or c for c in state["characters"].get("characters", [])],
                episodes=episode_objects,
            )
            state["screenplay"] = screenplay.model_dump(exclude_none=True)
            raw_yaml = screenplay_to_yaml(screenplay)
            raw_yaml = re.sub(r"^`(?:yaml)?\s*", "", raw_yaml)
            raw_yaml = re.sub(r"\s*`$", "", raw_yaml)
            state["screenplay_yaml"] = raw_yaml

            critic_out = self.critic_agent.retry({"screenplay": state["screenplay_yaml"]})
            state["violations"] = critic_out.get("violations", [])
            state["critic_score"] = critic_out.get("score", 1.0)

            errors = [v for v in state["violations"] if v.get("severity") == "error"]
            if errors:
                repair_out = self.repair_agent.retry({
                    "violations": state["violations"],
                    "screenplay": state["screenplay_yaml"],
                })
                state["repair_changes"].append("Applied auto-repair for violations")
                repaired_yaml = repair_out.get("yaml_output", "")
                repaired_yaml = re.sub(r"^`(?:yaml)?\s*", "", repaired_yaml)
                repaired_yaml = re.sub(r"\s*`$", "", repaired_yaml)
                if repaired_yaml:
                    state["screenplay_yaml"] = repaired_yaml
                    with contextlib.suppress(Exception):
                        state["screenplay"] = yaml.safe_load(repaired_yaml)

            state["completed"] = True

        except Exception as e:
            state["error"] = str(e)
            import traceback
            state["error"] += "\n" + traceback.format_exc()

        return state

    def run_consistency_check(self, novel_chunks: list[str], screenplay_yaml: str,
                              human_edits: str = "None") -> dict:
        """Run BidirectionalConsistencyAgent to compare novel vs screenplay."""
        try:
            return self.consistency_agent.run({
                "novel_chunks": novel_chunks,
                "screenplay": screenplay_yaml,
                "human_edits": human_edits,
            })
        except Exception as e:
            return {"alignment_score": 0.0, "deviations": [], "suggestions": [str(e)]}

    def save_export(self, state: dict, export_path: str) -> str:
        os.makedirs(export_path, exist_ok=True)
        filepath = os.path.join(export_path, f"{state['novel_title']}.screenplay.yaml")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(state["screenplay_yaml"])
        return filepath
