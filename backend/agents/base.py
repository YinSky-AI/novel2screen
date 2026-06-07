from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class AgentBase(ABC):
    def __init__(self, llm_client: Any, memory_manager: Any) -> None:
        self.llm = llm_client
        self.memory = memory_manager
        self._rag_enabled = True
        self._rag_top_k = 5
        self._retry_errors: list[str] = []

    @abstractmethod
    def run(self, input_data: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def validate(self, output: dict[str, Any]) -> bool: ...

    def validate_with_errors(self, output: dict[str, Any]) -> list[str]:
        return [] if self.validate(output) else ["Output failed validation"]

    def retry(self, input_data: dict[str, Any], max_attempts: int = 2) -> dict[str, Any]:
        last_output: dict[str, Any] = {}
        for attempt in range(max_attempts):
            if attempt > 0 and last_output:
                errors = self.validate_with_errors(last_output)
                input_data["_retry_errors"] = errors
                input_data["_previous_output"] = last_output
                logger.info("%s retrying with errors: %s", self.__class__.__name__, errors)
            try:
                output = self.run(input_data)
            except Exception:
                logger.exception("%s run() raised on attempt %d", self.__class__.__name__, attempt)
                if attempt == max_attempts - 1:
                    raise
                continue
            if self.validate(output):
                return output
            last_output = output
            logger.warning("%s validation failed on attempt %d", self.__class__.__name__, attempt)
        logger.error("%s exhausted all %d attempts", self.__class__.__name__, max_attempts)
        raise RuntimeError(f"{self.__class__.__name__}: failed after {max_attempts} attempts")

    # ---- RAG ----

    def _retrieve_context(self, query: str, top_k: int | None = None) -> str:
        if not self._rag_enabled:
            return ""
        try:
            result = self.memory.semantic.retrieve_context(query, top_k or self._rag_top_k)
            return result if isinstance(result, str) else ""
        except Exception:
            return ""

    def _build_rag_prompt(self, base_prompt: str, query: str) -> str:
        context = self._retrieve_context(query)
        if not context:
            return base_prompt
        if "{context}" in base_prompt:
            return base_prompt.replace("{context}", context[:3000])
        return f"[Reference excerpts from source text]\n{context[:3000]}\n\n---\n{base_prompt}"

    # ---- LLM ----

    def _call_llm(self, prompt: str, *, system_prompt: str = "", model: str = "", temperature: float = 0.7) -> str:
        messages: list[dict[str, str]] = [{"role": "user", "content": prompt}]
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})
        return self.llm.chat(messages, model=model, temperature=temperature)

    # ---- JSON ----

    def _parse_json(self, response: str) -> dict[str, Any]:
        return self.llm.extract_json(response)
