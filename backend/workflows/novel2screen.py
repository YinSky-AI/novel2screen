"""
Novel2Screen LangGraph Workflow.
Orchestrates the multi-agent pipeline for novel-to-screenplay conversion.
"""
from typing import TypedDict, Literal
import json
import yaml

from ..agents.narrative import NarrativeAgent
from ..agents.character import CharacterAgent
from ..agents.world import WorldAgent
from ..agents.timeline import TimelineAgent
from ..agents.episode_planner import EpisodePlannerAgent
from ..agents.scene_planner import ScenePlannerAgent
from ..agents.dialogue import DialogueAgent
from ..agents.critic import CriticAgent
from ..agents.repair import RepairAgent
from ..core.llm import llm_client
from ..schemas.validator import screenplay_to_yaml, yaml_to_screenplay
from ..schemas.models import Screenplay
from ..core.memory import ShortTermMemory, CharacterBible, WorldBible, SemanticMemory
from ..core.preprocessor import preprocess_novel, batch_plan_episodes
from ..core.prompts import FAST_CRITIC_SYSTEM, FAST_CRITIC_USER


# ── State Definition ──

class WorkflowState(TypedDict):
    """Shared state across all workflow nodes."""
    # Input
    novel_title: str
    novel_chunks: list[str]
    mode: Literal["short", "long"]
    genre: str

    # Agent outputs
    narrative: dict
    characters: dict
    world: dict
    timeline: dict
    episode_plan: dict
    scene_plans: list[dict]
    dialogue_scenes: list[dict]

    # Final screenplay
    screenplay_yaml: str
    screenplay: dict

    # Critic/Repair
    violations: list[dict]
    critic_score: float
    repair_changes: list[str]

    # Status
    error: str
    completed: bool


# ── Helper ──

def route_mode(num_chapters: int) -> str:
    """Route to short or long mode based on chapter count."""
    return "short" if 3 <= num_chapters <= 10 else "long"


# ── Graph Nodes ──

def parse_and_segment(novel_text: str, chunk_size: int = 3000) -> list[str]:
    """Split novel text into chapter chunks."""
    import re
    # Try to split by chapter markers
    chapters = re.split(r"(?:^|\n)#+\s*(?:第[一二三四五六七八九十百千万\d]+章|Chapter\s+\d+|[Cc]hapter\s+\d+)\s*[：:：]?\s*", novel_text, flags=re.MULTILINE)
    chapters = [c.strip() for c in chapters if c.strip()]
    # If no chapter markers found, split by paragraphs
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
        return chunks[:100]  # Safety cap
    return chapters


class Novel2ScreenWorkflow:
    """LangGraph-style workflow orchestrator."""

    def __init__(self, llm_client=None):
        # Agents
        self.narrative_agent = NarrativeAgent()
        self.character_agent = CharacterAgent()
        self.world_agent = WorldAgent()
        self.timeline_agent = TimelineAgent()
        self.episode_planner = EpisodePlannerAgent()
        self.scene_planner = ScenePlannerAgent()
        self.dialogue_agent = DialogueAgent()
        self.critic_agent = CriticAgent()
        self.repair_agent = RepairAgent()

        # Memory
        self.stm = ShortTermMemory()
        self.char_bible = CharacterBible()
        self.world_bible = WorldBible()
        self.sem_mem = SemanticMemory()

    def run(self, novel_text: str, novel_title: str = "Untitled", genre: str = "Drama", mode: str = "") -> dict:
        """Execute the full workflow."""
        state: WorkflowState = {
            "novel_title": novel_title,
            "novel_chunks": [],
            "mode": mode or "short",
            "genre": genre,
            "narrative": {},
            "characters": {},
            "world": {},
            "timeline": {},
            "episode_plan": {},
            "scene_plans": [],
            "dialogue_scenes": [],
            "screenplay_yaml": "",
            "screenplay": {},
            "violations": [],
            "critic_score": 1.0,
            "repair_changes": [],
            "error": "",
            "completed": False,
        }

        try:
            # 1. Parse and segment
            chunks = parse_and_segment(novel_text)
            state["novel_chunks"] = chunks
            num_chapters = len(chunks)

            if state["mode"] == "":
                state["mode"] = route_mode(num_chapters)

            # Index into semantic memory
            self.sem_mem.index(novel_text)

            # 2. NarrativeAgent
            state["narrative"] = self.narrative_agent.retry({"chunks": chunks})

            # 3. CharacterAgent
            state["characters"] = self.character_agent.retry({"content": novel_text[:8000]})
            for char in state["characters"].get("characters", []):
                self.char_bible.add_or_update(char)

            # 4. WorldAgent (long mode only)
            if state["mode"] == "long":
                state["world"] = self.world_agent.retry({"content": novel_text[:8000]})
                self.world_bible.set_rules(state["world"].get("world_rules", []))
                self.world_bible.set_geography(state["world"].get("geography", []))
            else:
                state["world"] = {"world_rules": [], "geography": []}

            # 5. TimelineAgent
            state["timeline"] = self.timeline_agent.retry({
                "major_events": state["narrative"].get("major_events", []),
                "mode": state["mode"],
            })

            # 6. EpisodePlanner
            state["episode_plan"] = self.episode_planner.retry({
                "narrative": state["narrative"],
                "characters": state["characters"].get("characters", []),
                "mode": state["mode"],
            })

            # 7. ScenePlanner + DialogueWriter for each episode
            state["scene_plans"] = []
            state["dialogue_scenes"] = []
            episodes = state["episode_plan"].get("episodes", [])

            for ep in episodes:
                ep_id = ep.get("id", "ep_001")
                # Scene planning
                scene_plan = self.scene_planner.retry({
                    "episode_id": ep_id,
                    "episode_title": ep.get("title", ""),
                    "episode_summary": ep.get("summary", ""),
                    "characters": state["characters"].get("characters", []),
                    "world_context": state["world"],
                })
                state["scene_plans"].append(scene_plan)

                # Dialogue writing for each scene
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

            # 8. Assemble Screenplay
            # Assign dialogue scenes to episodes properly
            dialogue_idx = 0
            episode_objects = []
            for ep in episodes:
                num_scenes = len(ep.get("scenes_in_episode", []))
                ep_scenes = state["dialogue_scenes"][dialogue_idx:dialogue_idx + num_scenes] if num_scenes > 0 else state["dialogue_scenes"][dialogue_idx:dialogue_idx + 3]
                dialogue_idx += len(ep_scenes) if len(ep_scenes) > 0 else 0
                episode_objects.append({
                    "id": ep["id"],
                    "title": ep["title"],
                    "summary": ep["summary"],
                    "scenes": ep_scenes if ep_scenes else state["dialogue_scenes"][:3],
                })
            
            # Fallback: if no scenes assigned, use ALL dialogue scenes for the first episode
            if not any(e["scenes"] for e in episode_objects):
                episode_objects[0]["scenes"] = state["dialogue_scenes"][:min(5, len(state["dialogue_scenes"]))]
            
            screenplay = Screenplay(
                title=state["novel_title"],
                logline=state["narrative"].get("theme", ""),
                genre=state["genre"],
                theme=state["narrative"].get("theme", ""),
                characters=[self.char_bible.get(c["id"]) or c for c in state["characters"].get("characters", [])],
                episodes=episode_objects,
            )

            state["screenplay"] = screenplay.model_dump(exclude_none=True)
            raw_yaml = screenplay_to_yaml(screenplay)
            # Strip markdown code blocks if present
            import re
            raw_yaml = re.sub(r'^`(?:yaml)?\s*', '', raw_yaml)
            raw_yaml = re.sub(r'\s*`$', '', raw_yaml)
            state["screenplay_yaml"] = raw_yaml

            # 9. CriticAgent
            critic_out = self.critic_agent.retry({"screenplay": state["screenplay_yaml"]})
            state["violations"] = critic_out.get("violations", [])
            state["critic_score"] = critic_out.get("score", 1.0)

            # 10. RepairAgent (if violations exist)
            errors = [v for v in state["violations"] if v.get("severity") == "error"]
            if errors:
                repair_out = self.repair_agent.retry({
                    "violations": state["violations"],
                    "screenplay": state["screenplay_yaml"],
                })
                state["repair_changes"].append("Applied auto-repair for violations")
                # Re-parse repaired YAML
                repaired_yaml = repair_out.get("yaml_output", "")
                repaired_yaml = re.sub(r'^`(?:yaml)?\s*', '', repaired_yaml)
                repaired_yaml = re.sub(r'\s*`$', '', repaired_yaml)
                if repaired_yaml:
                    state["screenplay_yaml"] = repaired_yaml
                    try:
                        state["screenplay"] = yaml.safe_load(repaired_yaml)
                    except Exception:
                        pass

            state["completed"] = True

        except Exception as e:
            state["error"] = str(e)
            import traceback
            state["error"] += "\n" + traceback.format_exc()

        return state

    def fast_run(self, novel_text: str, novel_title: str = "Untitled", genre: str = "Drama", mode: str = "") -> dict:
        """Optimized pipeline: 2-3 LLM calls instead of 9-15."""
        import re
        import json
        from ..schemas.validator import screenplay_to_yaml

        state = {
            "novel_title": novel_title, "novel_chunks": [], "mode": mode or "short",
            "genre": genre, "narrative": {}, "characters": {}, "world": {},
            "timeline": {}, "episode_plan": {}, "scene_plans": [], "dialogue_scenes": [],
            "screenplay_yaml": "", "screenplay": {}, "violations": [],
            "critic_score": 1.0, "repair_changes": [], "error": "", "completed": False,
        }

        try:
            # 1. Parse chapters
            chunks = parse_and_segment(novel_text)
            state["novel_chunks"] = chunks
            if state["mode"] == "":
                state["mode"] = route_mode(len(chunks))

            # 2. FAST PREPROCESS: 1 LLM call for narrative + characters + world
            pre = preprocess_novel(chunks)
            state["narrative"] = {"theme": pre["theme"], "major_events": pre["major_events"], "turning_points": pre["turning_points"]}
            state["characters"] = {"characters": pre["characters"]}
            state["world"] = {"geography": pre.get("locations", [])}

            # 3. BATCH PLAN: 1 LLM call for all episodes + scenes + dialogue
            plan = batch_plan_episodes(pre, state["mode"])
            state["episode_plan"] = {"episodes": plan.get("episodes", [])}

            # Build screenplay from batch plan
            from ..schemas.models import Screenplay
            raw_episodes = plan.get("episodes", [])
            if not raw_episodes:
                raw_episodes = [{"id": "ep_001", "title": novel_title or "Adaptation", "summary": "Auto-generated",
                    "scenes": [{"scene_id": "sc_001", "location": "Main", "time": "Unknown",
                        "beats": [{"type": "action", "content": "Opening."}],
                        "transition": "cut", "duration_estimate": "60s"}]}]

            # Post-process emotions and characters_present
            std_emos = {"anger","fear","joy","sadness","surprise","disgust","anticipation","calm","tension","confusion","resolve"}
            emo_map = {"震惊":"surprise","愤怒":"anger","恐惧":"fear","悲伤":"sadness","喜悦":"joy",
                       "怀疑":"tension","专注":"calm","紧张":"tension","决心":"resolve","困惑":"confusion",
                       "determined":"resolve","desperation":"fear","urgency":"tension","suspicion":"tension","determination":"resolve"}
            for ep in raw_episodes:
                ep.setdefault("scenes", [])
                for sc in ep.get("scenes", []):
                    if not sc.get("characters_present"):
                        cids = list(set(b.get("character_id") for b in sc.get("beats", []) if b.get("character_id")))
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
            state["screenplay"] = screenplay.model_dump(exclude_none=True)
            raw_yaml = screenplay_to_yaml(screenplay)
            raw_yaml = re.sub(r'^`(?:yaml)?\s*', '', raw_yaml)
            raw_yaml = re.sub(r'\s*`$', '', raw_yaml)
            state["screenplay_yaml"] = raw_yaml

            # 4. QUICK CRITIC + REPAIR: score and fix if needed
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
                critic_text = re.sub(r'^`(?:json)?\s*', '', critic_text)
                critic_text = re.sub(r'\s*`$', '', critic_text)
                critic_data = json.loads(critic_text)
                state["violations"] = critic_data.get("violations", [])
                state["critic_score"] = critic_data.get("score", 1.0)
            except Exception:
                state["critic_score"] = 0.9

            # Quality repair if score < 0.7
            if state["critic_score"] < 0.7:
                try:
                    from ..agents.repair import RepairAgent
                    ra = RepairAgent()
                    ro = ra.retry({"violations": state["violations"], "screenplay": state["screenplay_yaml"]})
                    ry = ro.get("yaml_output", "")
                    import re
                    ry = re.sub(r'^`(?:yaml)?\s*', '', ry)
                    ry = re.sub(r'\s*`$', '', ry)
                    if ry:
                        state["screenplay_yaml"] = ry
                        state["repair_changes"].append("Quality repair applied")
                except:
                    pass

            state["completed"] = True

        except Exception as e:
            state["error"] = str(e)
            import traceback
            state["error"] += "\n" + traceback.format_exc()

        return state

    def save_export(self, state: dict, export_path: str) -> str:
        """Save the final screenplay to a YAML file."""
        filepath = f"{export_path}/{state['novel_title']}.screenplay.yaml"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(state["screenplay_yaml"])
        return filepath
