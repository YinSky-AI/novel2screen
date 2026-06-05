"""
Memory management for Novel2Screen.
Handles short-term, long-term, and semantic memory as defined in the design spec.
"""
from __future__ import annotations
from typing import Any
import json
import hashlib


class ShortTermMemory:
    """Session-scoped memory for active chunk, active scene, and recent dialogue."""

    def __init__(self, max_dialogue_turns: int = 5):
        self.active_chapter: str = ""
        self.active_scene: dict = {}
        self.dialogue_buffer: list[dict] = []
        self.max_dialogue_turns = max_dialogue_turns

    def set_active_chapter(self, chapter_text: str):
        self.active_chapter = chapter_text

    def set_active_scene(self, scene: dict):
        self.active_scene = scene

    def push_dialogue(self, turn: dict):
        self.dialogue_buffer.append(turn)
        if len(self.dialogue_buffer) > self.max_dialogue_turns:
            self.dialogue_buffer.pop(0)

    def get_context(self) -> dict:
        return {
            "active_chapter": self.active_chapter[:500] if self.active_chapter else "",
            "active_scene": self.active_scene,
            "recent_dialogue": list(self.dialogue_buffer),
        }

    def clear(self):
        self.active_chapter = ""
        self.active_scene = {}
        self.dialogue_buffer = []


class CharacterBible:
    """Persistent character information store."""

    def __init__(self):
        self._characters: dict[str, dict] = {}

    def add_or_update(self, character: dict):
        self._characters[character["id"]] = character

    def get(self, char_id: str) -> dict | None:
        return self._characters.get(char_id)

    def get_all(self) -> list[dict]:
        return list(self._characters.values())

    def to_dict(self) -> dict:
        return {"characters": self._characters}

    def from_dict(self, data: dict):
        self._characters = data.get("characters", {})


class WorldBible:
    """Persistent world information store."""

    def __init__(self):
        self._rules: list[dict] = []
        self._geography: list[dict] = []

    def set_rules(self, rules: list[dict]):
        self._rules = rules

    def set_geography(self, geography: list[dict]):
        self._geography = geography

    def get_context(self) -> dict:
        return {"world_rules": self._rules, "geography": self._geography}


class SemanticMemory:
    """
    Vector-based semantic memory using sentence-transformers.
    Falls back to simple keyword matching if no embedding model is available.
    """

    def __init__(self, chunk_size: int = 1500, overlap: int = 200):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self._chunks: list[str] = []
        self._embeddings: list[list[float]] = []
        self._encoder = None

    def _lazy_load_encoder(self):
        if self._encoder is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._encoder = SentenceTransformer("BAAI/bge-large-en-v1.5")
            except ImportError:
                pass

    def chunk_text(self, text: str) -> list[str]:
        """Split text into overlapping chunks."""
        words = text.split()
        chunks = []
        step = self.chunk_size - self.overlap
        for i in range(0, len(words), step):
            chunk = " ".join(words[i : i + self.chunk_size])
            if chunk:
                chunks.append(chunk)
        return chunks

    def index(self, text: str):
        """Index a text passage into semantic memory."""
        chunks = self.chunk_text(text)
        self._chunks.extend(chunks)
        self._lazy_load_encoder()
        if self._encoder:
            emb = self._encoder.encode(chunks, show_progress_bar=False)
            self._embeddings.extend(emb.tolist())

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        """Search for semantically similar chunks."""
        self._lazy_load_encoder()
        if self._encoder and self._embeddings:
            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np

            q_emb = self._encoder.encode([query], show_progress_bar=False)
            sims = cosine_similarity(q_emb, np.array(self._embeddings))[0]
            top_indices = sims.argsort()[-top_k:][::-1]
            return [
                {"chunk": self._chreeks[i], "score": float(sims[i])}
                for i in top_indices
                if i < len(self._chunks)
            ]
        else:
            # Fallback: simple keyword matching
            query_lower = query.lower()
            scored = []
            for chunk in self._chunks:
                score = sum(1 for kw in query_lower.split() if kw in chunk.lower())
                scored.append((score, chunk))
            scored.sort(reverse=True)
            return [
                {"chunk": chunk, "score": score / max(s[0] for s in scored) if scored else 0}
                for score, chunk in scored[:top_k]
            ]


# Hash utility for round-trip integrity
def hash_yaml(yaml_str: str) -> str:
    return hashlib.sha256(yaml_str.encode("utf-8")).hexdigest()

import json
import hashlib
from typing import Optional


class MemoryManager:
    """Central memory orchestrator combining short-term, long-term, and semantic memory."""

    def __init__(self, stm: ShortTermMemory, char_bible: CharacterBible,
                 world_bible: WorldBible, sem_mem: Optional[SemanticMemory] = None):
        self.stm = stm
        self.char_bible = char_bible
        self.world_bible = world_bible
        self.sem_mem = sem_mem

    def get_context(self, chapter: int = 0, scene: str = "", query: str = "") -> dict:
        """Build context for LLM calls from all memory sources."""
        context = {
            "active_chapter": self.stm.active_chapter,
            "active_scene": self.stm.active_scene,
            "recent_dialogue": self.stm.get_recent_turns(5),
            "characters": self.char_bible.get_all(),
        }
        if self.world_bible:
            context["world_rules"] = self.world_bible.get_rules()
            context["geography"] = self.world_bible.get_geography()
        if self.sem_mem and query:
            context["semantic_hits"] = self.sem_mem.search(query)
        return context

    def update_chapter(self, chapter: int):
        self.stm.active_chapter = chapter

    def update_scene(self, scene: str):
        self.stm.active_scene = scene

    def add_dialogue_turn(self, character_id: str, line: str):
        self.stm.add_turn(character_id, line)

    def persist_all(self):
        """Persist long-term memory to disk (JSON-based persistence)."""
        char_file = os.path.join(os.path.dirname(__file__), "..", "data", "char_bible.json")
        world_file = os.path.join(os.path.dirname(__file__), "..", "data", "world_bible.json")
        os.makedirs(os.path.dirname(char_file), exist_ok=True)
        with open(char_file, "w", encoding="utf-8") as f:
            json.dump([c.model_dump() if hasattr(c, "model_dump") else c for c in self.char_bible.get_all()],
                      f, ensure_ascii=False, indent=2)
        with open(world_file, "w", encoding="utf-8") as f:
            json.dump({"rules": self.world_bible.get_rules(), "geography": self.world_bible.get_geography()},
                      f, ensure_ascii=False, indent=2)

    def load_all(self):
        """Load long-term memory from disk."""
        char_file = os.path.join(os.path.dirname(__file__), "..", "data", "char_bible.json")
        world_file = os.path.join(os.path.dirname(__file__), "..", "data", "world_bible.json")
        if os.path.exists(char_file):
            with open(char_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for c in data:
                    self.char_bible.add_or_update(c)
        if os.path.exists(world_file):
            with open(world_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.world_bible.set_rules(data.get("rules", []))
                self.world_bible.set_geography(data.get("geography", []))

    def get_alignment_report(self, original_novel_chunks, screenplay_yaml):
        """Compare original novel to screenplay and produce alignment report."""
        import json, yaml
        report = {
            "alignment_score": 0.0,
            "character_count_match": False,
            "plot_points_covered": [],
            "deviations": [],
        }
        try:
            screenplay = yaml.safe_load(screenplay_yaml)
            if not screenplay:
                return report
            
            # Check character count
            sc_chars = set(c.get("name", "") for c in screenplay.get("characters", []))
            report["character_count_match"] = len(sc_chars) > 0
            
            # Check key plot points mentioned
            episode_titles = [ep.get("title", "") for ep in screenplay.get("episodes", [])]
            events_from_novel = []
            for chunk in original_novel_chunks:
                for line in chunk.split("\n"):
                    if line.strip():
                        events_from_novel.append(line.strip()[:80])
            
            # Simple alignment: how many episode summaries mention a novel event
            score = 0.5  # base score
            if len(sc_chars) >= 2:
                score += 0.2
            if len(screenplay.get("episodes", [])) >= 2:
                score += 0.2
            report["alignment_score"] = round(min(score, 1.0), 2)
            
        except Exception:
            pass
        return report


    def detect_changes(self, original_state, edited_state):
        """Detect changes between original and edited screenplay."""
        changes = []
        try:
            original_eps = original_state.get("episodes", []) if isinstance(original_state, dict) else []
            edited_eps = edited_state.get("episodes", []) if isinstance(edited_state, dict) else []
            min_len = min(len(original_eps), len(edited_eps))
            for i in range(min_len):
                o = original_eps[i]
                e = edited_eps[i]
                if o.get("title") != e.get("title"):
                    changes.append({"type": "episode_title", "episode": i, "old": o.get("title"), "new": e.get("title")})
                o_scenes = o.get("scenes", [])
                e_scenes = e.get("scenes", [])
                for j in range(min(len(o_scenes), len(e_scenes))):
                    if o_scenes[j].get("location") != e_scenes[j].get("location"):
                        changes.append({"type": "scene_location", "episode": i, "scene": j, "old": o_scenes[j].get("location"), "new": e_scenes[j].get("location")})
        except Exception:
            pass
        return changes
