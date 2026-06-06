from __future__ import annotations

from backend.core.preprocessor import detect_language, estimate_tokens, parse_chapters, chunk_paragraphs


class NovelReader:
    def __init__(self, text: str) -> None:
        self.text = text
        self.language = detect_language(text)
        self.chapters = parse_chapters(text)
        self.token_estimate = estimate_tokens(text)

    def get_chapters(self) -> list[dict[str, str | int]]:
        return self.chapters

    def get_chunks(self, max_chars: int = 500) -> list[dict[str, str]]:
        return chunk_paragraphs(self.text, max_chars=max_chars)

    def get_summary(self) -> dict[str, int | str]:
        return {
            "language": self.language,
            "chapters_count": len(self.chapters),
            "token_estimate": self.token_estimate,
            "char_count": len(self.text),
        }


__all__ = ["NovelReader", "detect_language", "parse_chapters", "estimate_tokens", "chunk_paragraphs"]
