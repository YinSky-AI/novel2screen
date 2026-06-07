from __future__ import annotations

import json
import re
from typing import Any

from openai import OpenAI


class LLMClient:
    def __init__(self, api_key: str = "", base_url: str = "", model: str = "deepseek-chat") -> None:
        import os

        from backend.config import settings

        self._api_key = api_key or settings.DEEPSEEK_API_KEY or os.getenv("DEEPSEEK_API_KEY", "")
        self._base_url = base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        self._model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self._client = OpenAI(api_key=self._api_key, base_url=self._base_url)

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: dict[str, str] | None = None,
    ) -> str:
        target_model = model or self._model
        kwargs: dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format is not None:
            kwargs["response_format"] = response_format
        response = self._client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        return content if content is not None else ""

    def extract_json(self, text: str) -> dict[str, Any]:
        text = text.strip()
        fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if fence_match:
            text = fence_match.group(1).strip()
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            text = brace_match.group(0)
        try:
            text = self._repair_json(text)
            return json.loads(text)
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"JSON parse failed after repair ({e}): {text[:200]}") from e

    def repair_json(self, text: str) -> str:
        return self._repair_json(text)

    @staticmethod
    def _repair_json(text: str) -> str:
        text = text.strip()
        text = re.sub(r",\s*}", "}", text)
        text = re.sub(r",\s*]", "]", text)
        open_braces = text.count("{")
        close_braces = text.count("}")
        if open_braces > close_braces:
            text += "}" * (open_braces - close_braces)
        open_brackets = text.count("[")
        close_brackets = text.count("]")
        if open_brackets > close_brackets:
            text += "]" * (open_brackets - close_brackets)
        return text
