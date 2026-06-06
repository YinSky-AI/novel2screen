from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any


class AgentBase(ABC):
    def __init__(self, llm_client: Any, memory_manager: Any) -> None:
        self.llm = llm_client
        self.memory = memory_manager
        self._rag_enabled = True
        self._rag_top_k = 5
        self._retry_errors: list[str] = []
        self._previous_output: dict[str, Any] | None = None

    @abstractmethod
    def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        ...

    @abstractmethod
    def validate(self, output: dict[str, Any]) -> bool:
        ...

    def validate_with_errors(self, output: dict[str, Any]) -> list[str]:
        if self.validate(output):
            return []
        return ["Output failed validation"]

    def retry(self, input_data: dict[str, Any], max_attempts: int = 2) -> dict[str, Any]:
        for attempt in range(max_attempts):
            result = self.run(input_data)
            if self.validate(result):
                return result
            self._retry_errors = self.validate_with_errors(result)
            self._previous_output = result
        return self._previous_output or {}

    def _retrieve_context(self, query: str, top_k: int | None = None) -> list[str]:
        k = top_k if top_k is not None else self._rag_top_k
        try:
            return self.memory.semantic.retrieve_context(query, top_k=k)
        except Exception:
            return []

    def _build_rag_prompt(self, base_prompt: str, query: str) -> str:
        if not self._rag_enabled:
            return base_prompt
        contexts = self._retrieve_context(query)
        if not contexts:
            return base_prompt
        context_block = "\n\n".join(f"[Reference {i + 1}]\n{c}" for i, c in enumerate(contexts))
        return (
            "The following are reference excerpts from the source novel. Use them for "
            "grounding and factual accuracy:\n\n"
            f"{context_block}\n\n"
            "---\n\n"
            f"{base_prompt}"
        )

    def _call_llm(
        self, prompt: str, *, system_prompt: str = "", model: str = "", temperature: float = 0.7
    ) -> str:
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self.llm.chat(messages, model=model, temperature=temperature)

    def _parse_json(self, response: str) -> dict[str, Any]:
        return self.llm.extract_json(response)

    def _repair_json(self, text: str) -> str:
        return self.llm.repair_json(text)

    def _extract_json_from_text(self, text: str) -> dict[str, Any]:
        text = text.strip()
        fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if fence_match:
            text = fence_match.group(1).strip()
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            text = brace_match.group(0)
        text = self._repair_json(text)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            raise ValueError(f"Could not parse JSON from response: {text[:200]}")
