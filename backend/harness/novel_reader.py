from __future__ import annotations

from backend.core.preprocessor import detect_language, estimate_tokens, parse_chapters, smart_chunk


class NovelReader:
    def __init__(self, text: str) -> None:
        self.text = text
        self.language = detect_language(text)
        self.chapters = parse_chapters(text)
        self.token_estimate = estimate_tokens(text)

    def get_chapters(self) -> list[dict[str, str | int]]:
        return self.chapters

    def get_chunks(self, chunk_size: int = 1500, overlap: int = 200) -> list[str]:
        return smart_chunk(self.text, chunk_size=chunk_size, overlap=overlap)

    def get_summary(self) -> dict[str, int | str]:
        return {
            "language": self.language,
            "chapters_count": len(self.chapters),
            "token_estimate": self.token_estimate,
            "char_count": len(self.text),
        }


__all__ = ["NovelReader", "detect_language", "parse_chapters", "estimate_tokens", "smart_chunk"]
