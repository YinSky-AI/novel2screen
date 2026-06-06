from __future__ import annotations

import logging
import re
from typing import Any

from backend.core.memory import SemanticMemory

logger = logging.getLogger(__name__)


class RagMemory:
    def __init__(self, collection_name: str = "novel2screen_facts") -> None:
        self._semantic = SemanticMemory(collection_name=collection_name)

    def index_documents(self, documents: list[dict[str, Any]]) -> None:
        self._semantic.index(documents)

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        return self._semantic.search(query, top_k)

    def retrieve_context(self, query: str, top_k: int = 3, max_chars: int = 3000) -> str:
        return self._semantic.retrieve_context(query, top_k, max_chars)

    def search_characters(self, query: str, characters: list[dict[str, Any]], top_k: int = 5) -> list[dict[str, Any]]:
        results: list[tuple[int, dict[str, Any]]] = []
        for char in characters:
            score = self._character_match_score(query, char)
            if score > 0:
                results.append((score, char))
        results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in results[:top_k]]

    @staticmethod
    def _character_match_score(query: str, char: dict[str, Any]) -> int:
        score = 0
        query_lower = query.lower()
        name = char.get("name", "").lower()
        if name and name in query_lower:
            score += 10
        for field in ("role", "goal", "arc", "voice_style"):
            val = str(char.get(field, "")).lower()
            query_bigrams = {query_lower[i : i + 2] for i in range(len(query_lower) - 1)}
            val_bigrams = {val[j : j + 2] for j in range(len(val) - 1)}
            score += len(query_bigrams & val_bigrams)
        return score

    def verify_yaml_against_facts(self, yaml_content: str, facts: list[str]) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        for fact in facts:
            if fact.strip() and fact.strip() not in yaml_content:
                issues.append({
                    "type": "missing_fact",
                    "fact": fact.strip(),
                    "severity": "medium",
                    "suggestion": f"Include fact: {fact.strip()}",
                })
        return issues

    def chunk_and_index_text(self, text: str, metadata: dict[str, Any] | None = None) -> None:
        chunks = self._semantic.chunk_text(text)
        docs: list[dict[str, Any]] = []
        for i, chunk in enumerate(chunks):
            doc: dict[str, Any] = {"id": f"chunk_{i}", "content": chunk}
            if metadata:
                doc.update(metadata)
            docs.append(doc)
        self.index_documents(docs)
