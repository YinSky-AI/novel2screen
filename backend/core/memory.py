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
