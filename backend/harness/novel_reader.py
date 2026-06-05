"""Novel text processing: language detection, chapter parsing, smart chunking.
This is the first stage of the harness pipeline.
"""
import re


def detect_language(text: str) -> str:
    """Detect whether text is Chinese ('zh') or English ('en')."""
    if not text:
        return "en"
    # Count CJK characters
    sum(1 for c in text if "\u4e00" <= c <= "\u9fff" or "\u3000" <= c <= "\u303f")
    total_sampled = min(len(text), 2000)
    sample = text[:total_sampled]
    cjk_in_sample = sum(1 for c in sample if "\u4e00" <= c <= "\u9fff")
    ratio = cjk_in_sample / max(total_sampled, 1)
    return "zh" if ratio > 0.3 else "en"


def get_emotion_set(language: str) -> set:
    """Return allowed emotion labels matching novel language."""
    if language == "zh":
        return {"平静", "紧张", "震惊", "愤怒", "悲伤", "恐惧", "期待", "释然", "困惑", "决意", "喜悦"}
    return {"calm", "tension", "surprise", "anger", "sadness", "fear", "anticipation", "relief", "confusion", "resolve", "joy"}


def get_emotion_example(language: str) -> str:
    """Return a human-readable list for prompt injection."""
    if language == "zh":
        return "平静, 紧张, 震惊, 愤怒, 悲伤, 恐惧, 期待, 释然, 困惑, 决意, 喜悦"
    return "calm, tension, surprise, anger, sadness, fear, anticipation, relief, confusion, resolve, joy"


CHAPTER_PATTERNS = [
    # Chinese: 第一章 / # 第一章 / 第1章
    r"(?:^|\n)\s*(?:#\s*)?第[一二三四五六七八九十百千万零\d]+[章回部]\s*[：: ．\s]?",
    # English: Chapter 1 / # Chapter 1 / CHAPTER I / chapter one
    r"(?:^|\n)\s*(?:#\s*)?(?:Chapter|CHAPTER|chapter|Ch\.|CH\.)\s+[\dIVXLCDM]+[：: ．\s]?",
    # English: Part I / Section 1
    r"(?:^|\n)\s*(?:#\s*)?(?:Part|PART|part|Section|SECTION|section)\s+[\dIVXLCDM]+[：: ．\s]?",
]


def parse_chapters(text: str) -> list[dict]:
    """Split novel into chapters with metadata.

    Returns list of dicts: [{index, title, content, char_count}]
    """
    if not text or not text.strip():
        return []

    # Try each pattern, use the one that produces the most splits (>= 3)
    best_splits = None
    best_raw_splits = []

    for pattern in CHAPTER_PATTERNS:
        raw_splits = re.split(pattern, text, flags=re.MULTILINE)
        splits = [s.strip() for s in raw_splits if s.strip()]
        # raw_splits may start with '' (match at start); need at least 3 raw elements to form 2+ chapters
        if len(raw_splits) >= 3 and (not best_splits or len(raw_splits) > len(best_raw_splits)):
            best_splits = splits
            best_raw_splits = raw_splits

    if best_splits:
        chapters = []
        for i, content in enumerate(best_splits):
            chapters.append({
                "index": i + 1,
                "title": f"Chapter {i + 1}",
                "content": content,
                "char_count": len(content),
            })
        return chapters

    # Fallback: split by double newline paragraphs and group
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paragraphs) >= 6:
        # Group paragraphs into ~equal chunks, each ~2000 chars
        chapters = []
        current = []
        current_len = 0
        target = max(1500, sum(len(p) for p in paragraphs) // max(len(paragraphs) // 4, 1))
        for p in paragraphs:
            current.append(p)
            current_len += len(p)
            if current_len >= target:
                chapters.append({
                    "index": len(chapters) + 1,
                    "title": f"Chapter {len(chapters) + 1}",
                    "content": "\n\n".join(current),
                    "char_count": current_len,
                })
                current = []
                current_len = 0
        if current:
            chapters.append({
                "index": len(chapters) + 1,
                "title": f"Chapter {len(chapters) + 1}",
                "content": "\n\n".join(current),
                "char_count": current_len,
            })
        return chapters

    # Last resort: single chapter
    return [{
        "index": 1,
        "title": "Chapter 1",
        "content": text,
        "char_count": len(text),
    }]


def estimate_tokens(text: str) -> int:
    """Rough token estimate: 1 token ≈ 4 chars for EN, ≈ 2 chars for ZH."""
    cjk = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    ascii_chars = len(text) - cjk
    return cjk // 2 + ascii_chars // 4


def smart_chunk(chapters: list[dict], max_tokens: int = 30000, overlap_chapters: int = 2) -> list[dict]:
    """Token-aware chunking that respects chapter boundaries.

    Each chunk keeps overlap_chapters of context from the previous chunk.
    Returns list of dicts: [{chunk_index, chapters: [chapter_dicts], total_tokens}]
    """
    if not chapters:
        return []

    chunks = []
    current_chunks = []
    current_tokens = 0

    for ch in chapters:
        ch_tokens = estimate_tokens(ch["content"])
        if current_tokens + ch_tokens > max_tokens and current_chunks:
            chunks.append({
                "chunk_index": len(chunks) + 1,
                "chapters": list(current_chunks),
                "total_tokens": current_tokens,
                "chapter_range": f"{current_chunks[0]['index']}-{current_chunks[-1]['index']}",
            })
            # Keep overlap chapters for continuity
            overlap = current_chunks[-overlap_chapters:] if overlap_chapters > 0 else []
            current_chunks = list(overlap)
            current_tokens = sum(estimate_tokens(c["content"]) for c in overlap)
        current_chunks.append(ch)
        current_tokens += ch_tokens

    if current_chunks:
        chunks.append({
            "chunk_index": len(chunks) + 1,
            "chapters": list(current_chunks),
            "total_tokens": current_tokens,
            "chapter_range": f"{current_chunks[0]['index']}-{current_chunks[-1]['index']}",
        })

    return chunks


def extract_ending(text: str, ratio: float = 0.1, min_chars: int = 100) -> str:
    """Extract the last ratio of the novel for ending verification."""
    if not text:
        return ""
    if len(text) <= min_chars:
        return text.strip()
    pos = int(len(text) * (1 - ratio))
    return text[pos:].strip()


def extract_beginning(text: str, ratio: float = 0.15) -> str:
    """Extract the first ratio of the novel for tone/character extraction."""
    if not text:
        return ""
    return text[:int(len(text) * ratio)].strip()


def chapters_to_text(chapters: list[dict]) -> str:
    """Convert chapter list to formatted text for LLM input."""
    parts = []
    for ch in chapters:
        parts.append(f"Chapter {ch['index']}:\n{ch['content']}")
    return "\n\n---\n\n".join(parts)


def summarize_chapters(chapters: list[dict], max_chars_per_chapter: int = 2000) -> str:
    """Truncate each chapter to a max length and format."""
    parts = []
    for ch in chapters:
        content = ch["content"][:max_chars_per_chapter]
        if len(ch["content"]) > max_chars_per_chapter:
            content += "\n...[truncated]"
        parts.append(f"Chapter {ch['index']}:\n{content}")
    return "\n\n---\n\n".join(parts)
