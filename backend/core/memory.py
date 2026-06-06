from __future__ import annotations

import json
import logging
import os
import pickle
import re
from typing import Any

from backend.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Short-Term Memory
# ---------------------------------------------------------------------------


class ShortTermMemory:
    def __init__(self, max_turns: int = 5) -> None:
        self._max_turns: int = max_turns
        self._dialogue_buffer: list[dict[str, Any]] = []
        self._active_chapter: str = ""
        self._active_scene: dict[str, Any] = {}
        self._context: dict[str, Any] = {}

    def add_turn(self, role: str, content: str) -> None:
        self._dialogue_buffer.append({"role": role, "content": content})
        if len(self._dialogue_buffer) > self._max_turns * 2:
            self._dialogue_buffer = self._dialogue_buffer[-(self._max_turns * 2):]

    def get_history(self) -> list[dict[str, Any]]:
        return list(self._dialogue_buffer)

    def set_active_chapter(self, chapter: str) -> None:
        self._active_chapter = chapter

    def set_active_scene(self, scene: dict[str, Any]) -> None:
        self._active_scene = scene

    def get_active_chapter(self) -> str:
        return self._active_chapter

    def get_active_scene(self) -> dict[str, Any]:
        return dict(self._active_scene)

    def set_context(self, key: str, value: Any) -> None:
        self._context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        return self._context.get(key, default)

    def clear(self) -> None:
        self._dialogue_buffer.clear()
        self._active_scene.clear()
        self._context.clear()

    def to_dict(self) -> dict[str, Any]:
        return {
            "dialogue_buffer": self._dialogue_buffer,
            "active_chapter": self._active_chapter,
            "active_scene": self._active_scene,
            "context": self._context,
        }

    def from_dict(self, data: dict[str, Any]) -> None:
        self._dialogue_buffer = data.get("dialogue_buffer", [])
        self._active_chapter = data.get("active_chapter", "")
        self._active_scene = data.get("active_scene", {})
        self._context = data.get("context", {})


# ---------------------------------------------------------------------------
# Character Bible
# ---------------------------------------------------------------------------


class CharacterBible:
    def __init__(self) -> None:
        self._characters: dict[str, dict[str, Any]] = {}

    def save(self, char_id: str, data: dict[str, Any]) -> None:
        self._characters[char_id] = dict(data)

    def load(self, char_id: str) -> dict[str, Any] | None:
        return self._characters.get(char_id)

    def get_all(self) -> dict[str, dict[str, Any]]:
        return dict(self._characters)

    def get_by_name(self, name: str) -> dict[str, Any] | None:
        for char_data in self._characters.values():
            if char_data.get("name", "").lower() == name.lower():
                return dict(char_data)
        return None

    def remove(self, char_id: str) -> None:
        self._characters.pop(char_id, None)

    def update(self, char_id: str, updates: dict[str, Any]) -> None:
        if char_id in self._characters:
            self._characters[char_id].update(updates)
        else:
            self._characters[char_id] = dict(updates)

    def to_dict(self) -> dict[str, Any]:
        return {"characters": dict(self._characters)}

    def from_dict(self, data: dict[str, Any]) -> None:
        self._characters = data.get("characters", {})


# ---------------------------------------------------------------------------
# World Bible
# ---------------------------------------------------------------------------


class WorldBible:
    def __init__(self) -> None:
        self._world_rules: dict[str, Any] = {}
        self._geography: list[dict[str, Any]] = []

    def set_rule(self, rule_id: str, rule_data: dict[str, Any]) -> None:
        self._world_rules[rule_id] = dict(rule_data)

    def get_rule(self, rule_id: str) -> dict[str, Any] | None:
        return self._world_rules.get(rule_id)

    def get_all_rules(self) -> dict[str, Any]:
        return dict(self._world_rules)

    def add_location(self, location: dict[str, Any]) -> None:
        self._geography.append(dict(location))

    def get_locations(self) -> list[dict[str, Any]]:
        return list(self._geography)

    def get_location(self, name: str) -> dict[str, Any] | None:
        for loc in self._geography:
            if loc.get("name", "").lower() == name.lower():
                return dict(loc)
        return None

    def to_dict(self) -> dict[str, Any]:
        return {"world_rules": dict(self._world_rules), "geography": list(self._geography)}

    def from_dict(self, data: dict[str, Any]) -> None:
        self._world_rules = data.get("world_rules", {})
        self._geography = data.get("geography", [])


# ---------------------------------------------------------------------------
# Semantic Memory (ChromaDB)
# ---------------------------------------------------------------------------


class SemanticMemory:
    def __init__(self, collection_name: str = "novel2screen") -> None:
        self._collection_name: str = collection_name
        self._client: Any = None
        self._collection: Any = None
        self._embed_model: Any = None
        self._embed_failed: bool = False
        self._documents: list[dict[str, Any]] = []
        self._initialized: bool = False

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        persist_dir = settings.CHROMA_PERSIST_DIR
        try:
            os.makedirs(persist_dir, exist_ok=True)
            import chromadb

            self._client = chromadb.PersistentClient(path=persist_dir)
            existing = [c.name for c in self._client.list_collections()]
            if self._collection_name not in existing:
                self._collection = self._client.create_collection(name=self._collection_name)
            else:
                self._collection = self._client.get_collection(name=self._collection_name)
            logger.info("ChromaDB initialized at %s", persist_dir)
        except Exception as e:
            logger.warning("ChromaDB init failed, using in-memory fallback: %s", e)
            self._client = None
            self._collection = None

        self._get_embed_fn()

    def _get_embed_fn(self) -> None:
        if self._embed_failed:
            return None
        if self._embed_model is not None:
            return
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
        try:
            from sentence_transformers import SentenceTransformer

            self._embed_model = SentenceTransformer(
                settings.EMBEDDING_MODEL,
                device="cpu",
            )
            logger.info("Embedding model loaded: %s", settings.EMBEDDING_MODEL)
        except Exception as e:
            logger.warning("Failed to load embedding model: %s", e)
            self._embed_failed = True
            self._embed_model = None

    def _embed(self, texts: list[str]) -> list[list[float]]:
        if self._embed_failed or self._embed_model is None:
            return [[0.0]] * len(texts)
        try:
            embeddings = self._embed_model.encode(texts, convert_to_numpy=True)
            return [emb.tolist() for emb in embeddings]
        except Exception as e:
            logger.warning("Embedding encode failed: %s", e)
            self._embed_failed = True
            return [[0.0]] * len(texts)

    def chunk_text(self, text: str, chunk_size: int | None = None, overlap: int | None = None) -> list[str]:
        if chunk_size is None:
            chunk_size = settings.CHUNK_SIZE
        if overlap is None:
            overlap = settings.CHUNK_OVERLAP
        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append(text[start:end])
            if end >= len(text):
                break
            start = end - overlap
        return chunks

    def index(self, documents: list[dict[str, Any]]) -> None:
        if not documents:
            return
        self._ensure_initialized()
        self._documents = list(documents)
        if self._collection is None or self._embed_failed:
            return
        try:
            ids: list[str] = []
            contents: list[str] = []
            metadatas: list[dict[str, Any]] = []
            for i, doc in enumerate(documents):
                doc_id = doc.get("id", f"doc_{i}")
                ids.append(doc_id)
                contents.append(doc.get("content", doc.get("text", "")))
                metadatas.append({k: str(v) for k, v in doc.items() if k not in ("id", "content", "text")})
            embeddings = self._embed(contents)
            if self._embed_failed:
                return
            self._collection.upsert(ids=ids, documents=contents, metadatas=metadatas, embeddings=embeddings)
            logger.info("Indexed %d documents into ChromaDB", len(documents))
        except Exception as e:
            logger.warning("ChromaDB index failed: %s", e)

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        self._ensure_initialized()
        if self._collection is None or self._embed_failed:
            return self._jaccard_search_cjk(query, top_k)
        try:
            emb = self._embed([query])
            if self._embed_failed:
                return self._jaccard_search_cjk(query, top_k)
            results = self._collection.query(query_embeddings=emb, n_results=top_k)
            hits: list[dict[str, Any]] = []
            if results and results["ids"] and results["ids"][0]:
                for i, doc_id in enumerate(results["ids"][0]):
                    hits.append({
                        "id": doc_id,
                        "content": results["documents"][0][i] if results.get("documents") else "",
                        "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                        "distance": results["distances"][0][i] if results.get("distances") else 0.0,
                    })
            return hits
        except Exception as e:
            logger.warning("ChromaDB search failed, using CJK keyword fallback: %s", e)
            return self._jaccard_search_cjk(query, top_k)

    def retrieve_context(self, query: str, top_k: int = 3, max_chars: int = 3000) -> str:
        results = self.search(query, top_k)
        parts: list[str] = []
        total = 0
        for r in results:
            content = r.get("content", "")
            if total + len(content) > max_chars:
                content = content[:max_chars - total] + "..."
            parts.append(content)
            total += len(content)
            if total >= max_chars:
                break
        return "\n---\n".join(parts)

    @staticmethod
    def _keyword_search(query: str, top_k: int = 5) -> list[dict[str, Any]]:
        return [{"id": "kw_fallback", "content": f"No semantic results for: {query}", "metadata": {}, "distance": 1.0}]

    def _jaccard_search_cjk(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Bigram-based search suitable for Chinese/CJK text."""
        def _bigrams(text: str) -> set[str]:
            clean = re.sub(r"\s+", "", text)
            return {clean[i:i+2] for i in range(len(clean)-1)} if len(clean) >= 2 else set()

        q_bigrams = _bigrams(query)
        if not q_bigrams or not self._documents:
            return []

        scored = []
        for doc in self._documents:
            content = doc.get("content", doc.get("text", ""))
            if not content:
                continue
            d_bigrams = _bigrams(content)
            if not d_bigrams:
                continue
            jaccard = len(q_bigrams & d_bigrams) / len(q_bigrams | d_bigrams)
            scored.append((jaccard, {"content": content, "id": doc.get("id", ""), "distance": 1.0 - jaccard}))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:top_k] if item["content"]]

    def jaccard_search(self, query: str, documents: list[str], top_k: int = 5) -> list[str]:
        def _jaccard(a: set[str], b: set[str]) -> float:
            if not a or not b:
                return 0.0
            return len(a & b) / len(a | b)

        query_set = set(query.lower().split())
        scored = [(doc, _jaccard(query_set, set(doc.lower().split()))) for doc in documents]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in scored[:top_k]]

    def clear(self) -> None:
        self._documents = []
        if self._collection is not None:
            try:
                self._collection.delete(ids=self._collection.get()['ids'])
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Memory Manager
# ---------------------------------------------------------------------------


class MemoryManager:
    def __init__(self) -> None:
        self.stm = ShortTermMemory()
        self.characters = CharacterBible()
        self.world = WorldBible()
        self.semantic = SemanticMemory()
        self._store: dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        self._store[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._store.get(key, default)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def detect_changes(self, old_state: dict[str, Any], new_state: dict[str, Any]) -> list[str]:
        changes: list[str] = []
        all_keys = set(old_state.keys()) | set(new_state.keys())
        for key in all_keys:
            old_val = old_state.get(key)
            new_val = new_state.get(key)
            if old_val != new_val:
                changes.append(key)
        return changes

    def save(self, filepath: str) -> None:
        data: dict[str, Any] = {
            "stm": self.stm.to_dict(),
            "characters": self.characters.to_dict(),
            "world": self.world.to_dict(),
            "store": dict(self._store),
        }
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "wb") as f:
            pickle.dump(data, f)
        logger.info("Memory state saved to %s", filepath)

    def load(self, filepath: str) -> bool:
        if not os.path.exists(filepath):
            return False
        try:
            with open(filepath, "rb") as f:
                data = pickle.load(f)
            self.stm.from_dict(data.get("stm", {}))
            self.characters.from_dict(data.get("characters", {}))
            self.world.from_dict(data.get("world", {}))
            self._store = data.get("store", {})
            logger.info("Memory state loaded from %s", filepath)
            return True
        except Exception as e:
            logger.warning("Failed to load memory state: %s", e)
            return False
