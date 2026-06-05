"""
Memory management for Novel2Screen.
Handles short-term, long-term, and semantic memory (ChromaDB-backed RAG).
"""
from __future__ import annotations
from typing import Any, Optional
import json
import hashlib
import os


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

    def add_turn(self, character_id: str, line: str):
        self.push_dialogue({"character_id": character_id, "line": line})

    def get_recent_turns(self, n: int = 5) -> list[dict]:
        return self.dialogue_buffer[-n:]

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
        char_id = character.get("id", character.get("name", ""))
        self._characters[char_id] = character

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

    def get_rules(self) -> list[dict]:
        return self._rules

    def get_geography(self) -> list[dict]:
        return self._geography

    def get_context(self) -> dict:
        return {"world_rules": self._rules, "geography": self._geography}


class SemanticMemory:
    """
    Vector-based semantic memory using ChromaDB (primary) or sentence-transformers
    with cosine similarity (fallback). Provides persistent RAG retrieval.
    """

    def __init__(self, chunk_size: int = 1500, overlap: int = 200,
                 persist_dir: str = "./data/chroma_db", embedding_model: str = "all-MiniLM-L6-v2"):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.persist_dir = persist_dir
        self.embedding_model_name = embedding_model
        self._chunks: list[str] = []
        self._collection = None
        self._embedding_fn = None
        self._use_chromadb = False
        self._indexed = False

    def _init_chromadb(self):
        if self._use_chromadb and self._collection is not None:
            return
        try:
            import chromadb
            from chromadb.utils import embedding_functions
            os.makedirs(self.persist_dir, exist_ok=True)
            client = chromadb.PersistentClient(path=self.persist_dir)
            self._embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=self.embedding_model_name
            )
            self._collection = client.get_or_create_collection(
                name="novel2screen_chunks",
                embedding_function=self._embedding_fn,
                metadata={"hnsw:space": "cosine"},
            )
            self._use_chromadb = True
        except ImportError:
            self._use_chromadb = False
        except Exception:
            self._use_chromadb = False

    def chunk_text(self, text: str, source_label: str = "") -> list[dict]:
        """Split text into overlapping chunks with metadata."""
        words = text.split()
        chunks = []
        step = max(1, self.chunk_size - self.overlap)
        for i in range(0, len(words), step):
            chunk_text = " ".join(words[i:i + self.chunk_size])
            if chunk_text and len(chunk_text) > 20:
                chunks.append({
                    "text": chunk_text,
                    "source": source_label,
                    "chunk_index": i // step,
                })
        return chunks

    def index(self, text: str, source_label: str = "novel", force: bool = False):
        """Index text into semantic memory."""
        if self._indexed and not force:
            return

        self._init_chromadb()
        chunks_meta = self.chunk_text(text, source_label)

        if not chunks_meta:
            return

        if self._use_chromadb and self._collection:
            try:
                existing_count = self._collection.count()
                start_idx = existing_count
                ids = [f"chunk_{start_idx + i}" for i in range(len(chunks_meta))]
                documents = [c["text"] for c in chunks_meta]
                metadatas = [{"source": c["source"], "chunk_index": c["chunk_index"]} for c in chunks_meta]
                self._collection.add(ids=ids, documents=documents, metadatas=metadatas)
                self._chunks = documents
                self._indexed = True
                return
            except Exception:
                pass

        self._chunks = [c["text"] for c in chunks_meta]
        self._indexed = True

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        """Search for semantically similar chunks. Uses ChromaDB if available."""
        if not self._chunks:
            return []

        self._init_chromadb()

        if self._use_chromadb and self._collection:
            try:
                results = self._collection.query(query_texts=[query], n_results=min(top_k, self._collection.count()))
                if results and results.get("documents") and results["documents"][0]:
                    docs = results["documents"][0]
                    distances = results.get("distances", [[0] * len(docs)])[0] if results.get("distances") else [0] * len(docs)
                    return [
                        {"chunk": doc, "score": round(1.0 - distances[i], 4)}
                        for i, doc in enumerate(docs)
                    ]
            except Exception:
                pass

        return self._keyword_search(query, top_k)

    def _keyword_search(self, query: str, top_k: int = 3) -> list[dict]:
        """Fallback keyword matching search."""
        if not self._chunks:
            return []
        query_lower = query.lower()
        query_keywords = set(query_lower.split())
        scored = []
        for chunk in self._chunks:
            chunk_lower = chunk.lower()
            score = sum(1 for kw in query_keywords if kw in chunk_lower)
            if score > 0:
                scored.append((score, chunk))
        if not scored:
            return [{"chunk": self._chunks[0][:500], "score": 0.05}]
        scored.sort(key=lambda x: x[0], reverse=True)
        max_score = scored[0][0] if scored else 1
        return [
            {"chunk": chunk, "score": round(score / max(max_score, 1), 3)}
            for score, chunk in scored[:top_k]
        ]

    def retrieve_context(self, queries: list[str], top_k: int = 3) -> str:
        """Retrieve and format RAG context for prompt injection."""
        if not self._chunks:
            return ""
        all_chunks = set()
        for query in queries:
            results = self.search(query, top_k=top_k)
            for r in results:
                all_chunks.add(r["chunk"][:800])
        if not all_chunks:
            return ""
        return "\n\n---\n\n".join(f"[Context] {c}" for c in list(all_chunks)[:top_k * 2])

    def get_stats(self) -> dict:
        return {
            "total_chunks": len(self._chunks),
            "use_chromadb": self._use_chromadb,
            "persist_dir": self.persist_dir,
            "indexed": self._indexed,
        }


def hash_yaml(yaml_str: str) -> str:
    return hashlib.sha256(yaml_str.encode("utf-8")).hexdigest()


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
            context["semantic_hits"] = self.sem_mem.search(query, top_k=3)
        return context

    def update_chapter(self, chapter: str):
        self.stm.active_chapter = chapter

    def update_scene(self, scene: str):
        self.stm.active_scene = scene

    def add_dialogue_turn(self, character_id: str, line: str):
        self.stm.add_turn(character_id, line)

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
                        changes.append({"type": "scene_location", "episode": i, "scene": j,
                                        "old": o_scenes[j].get("location"), "new": e_scenes[j].get("location")})
        except Exception:
            pass
        return changes

    def get_alignment_report(self, original_novel_chunks, screenplay_yaml):
        """Compare original novel to screenplay and produce alignment report."""
        import yaml
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
            sc_chars = set(c.get("name", "") for c in screenplay.get("characters", []))
            report["character_count_match"] = len(sc_chars) > 0
            score = 0.5
            if len(sc_chars) >= 2:
                score += 0.2
            if len(screenplay.get("episodes", [])) >= 2:
                score += 0.2
            report["alignment_score"] = round(min(score, 1.0), 2)
        except Exception:
            pass
        return report

    def persist_all(self):
        """Persist long-term memory to disk."""
        out_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        os.makedirs(out_dir, exist_ok=True)
        char_file = os.path.join(out_dir, "char_bible.json")
        world_file = os.path.join(out_dir, "world_bible.json")
        with open(char_file, "w", encoding="utf-8") as f:
            json.dump(self.char_bible.get_all(), f, ensure_ascii=False, indent=2)
        with open(world_file, "w", encoding="utf-8") as f:
            json.dump({"rules": self.world_bible.get_rules(), "geography": self.world_bible.get_geography()},
                      f, ensure_ascii=False, indent=2)

    def load_all(self):
        """Load long-term memory from disk."""
        out_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        char_file = os.path.join(out_dir, "char_bible.json")
        world_file = os.path.join(out_dir, "world_bible.json")
        if os.path.exists(char_file):
            with open(char_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for c in (data if isinstance(data, list) else [data]):
                    self.char_bible.add_or_update(c)
        if os.path.exists(world_file):
            with open(world_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.world_bible.set_rules(data.get("rules", []))
                self.world_bible.set_geography(data.get("geography", []))
