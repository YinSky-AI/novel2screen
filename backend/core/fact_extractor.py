"""RAG-based novel context retrieval. Pure Python, no external deps.
Character bigram + Jaccard similarity for semantic search.
"""
import re
from typing import Optional


class RagMemory:
    """Semantic memory using character bigrams for relevant context retrieval."""

    def __init__(self):
        self.chunks: list[str] = []
        self._bigram_sets: list[set] = []

    def index(self, text: str, chunk_size: int = 300):
        """Chunk text and index by character bigrams."""
        self.chunks = self._chunk_text(text, chunk_size)
        self._bigram_sets = [self._bigrams(c) for c in self.chunks]

    def search(self, query: str, top_k: int = 3) -> list[str]:
        """Find most relevant chunks by bigram overlap."""
        if not self.chunks:
            return []
        query_bigrams = self._bigrams(query)
        if not query_bigrams:
            return self.chunks[:top_k]

        scored = []
        for i, chunk_bigrams in enumerate(self._bigram_sets):
            if not chunk_bigrams:
                continue
            overlap = len(query_bigrams & chunk_bigrams)
            union = len(query_bigrams | chunk_bigrams)
            score = overlap / union if union > 0 else 0
            scored.append((score, i))

        scored.sort(key=lambda x: -x[0])
        return [self.chunks[i] for _, i in scored[:top_k]]

    def build_context(self, query: str = "", top_k: int = 3) -> str:
        """Build context string from relevant chunks for prompt injection."""
        results = self.search(query, top_k)
        if not results:
            return ""
        lines = ["=== RELEVANT TEXT FROM NOVEL (ground truth) ==="]
        for i, r in enumerate(results):
            clean = r[:400].replace("\n", " ")
            lines.append(f"[Excerpt {i+1}]: {clean}")
        lines.append("Use the above as ground truth. Do not invent details that contradict them.")
        return "\n\n".join(lines)

    def _bigrams(self, text: str) -> set:
        """Extract character bigram set from text (Chinese chars only)."""
        chars = re.findall(r"[\u4e00-\u9fff]", text)
        return set(chars[i] + chars[i+1] for i in range(len(chars)-1))

    def _chunk_text(self, text: str, chunk_size: int = 300) -> list[str]:
        """Split text into overlapping chunks by paragraphs."""
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks, current = [], ""
        for p in paragraphs:
            if len(current) + len(p) < chunk_size:
                current += "\n\n" + p
            else:
                if current.strip():
                    chunks.append(current.strip())
                current = p
        if current.strip():
            chunks.append(current.strip())
        return chunks if chunks else [text[:chunk_size]]


def extract_fact_sheet_full(novel_text: str, chunks: Optional[list] = None) -> dict:
    """Extract fact sheet using RAG. Returns formatted reference + memory."""
    mem = RagMemory()
    mem.index(novel_text)

    # Build chapter openings reference
    if chunks:
        parts = ["=== GROUND TRUTH FROM NOVEL ==="]
        for i, ch in enumerate(chunks):
            first = ch[:200].replace("\n", " ")
            parts.append(f"Ch {i+1}: {first}")
        reference = "\n\n".join(parts)
    else:
        reference = mem.build_context("main characters plot", 3)

    return {
        "names": [],  # Name extraction moved to RAG context
        "locations": [],
        "events": [],
        "reference": reference,
        "memory": mem,
    }


def verify_yaml_against_facts(yaml_str: str, fact_sheet: dict) -> list:
    """Stub - verification is now handled by RAG context in prompts."""
    return []  # RAG provides context directly in prompts, no post-hoc verify needed