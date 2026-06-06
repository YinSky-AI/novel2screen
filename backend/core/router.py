from __future__ import annotations

import logging
import time
from typing import Any

from backend.core.llm import LLMClient

logger = logging.getLogger(__name__)

_AGENT_MODEL_MAP: dict[str, str] = {
    "Narrative": "claude-3-haiku-20240307",
    "Character": "gpt-3.5-turbo",
    "World": "claude-3-sonnet-20240229",
    "ScenePlanner": "gpt-4-turbo",
    "Dialogue": "claude-3-haiku-20240307",
    "Critic": "gpt-4-turbo",
    "Repair": "gpt-3.5-turbo",
    "Consistency": "claude-3-haiku-20240307",
    "Preprocess": "claude-3-sonnet-20240229",
    "BatchPlan": "gpt-4-turbo",
    "Timeline": "claude-3-haiku-20240307",
}


class ModelRouter:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self._clients: dict[str, LLMClient] = {}
        self._default_client = llm_client or LLMClient()

    def resolve_model(self, agent_name: str) -> str:
        return _AGENT_MODEL_MAP.get(agent_name, "gpt-3.5-turbo")

    def execute(
        self,
        agent_name: str,
        prompt: str,
        system_prompt: str = "",
        max_retries: int = 2,
    ) -> str:
        model = self.resolve_model(agent_name)
        if agent_name not in self._clients:
            self._clients[agent_name] = LLMClient(model_name=model)

        client = self._clients[agent_name]
        last_error: Exception | None = None

        for attempt in range(max_retries + 1):
            try:
                result = client.generate(prompt=prompt, system_prompt=system_prompt)
                return result
            except Exception as e:
                last_error = e
                logger.warning(
                    "Agent %s attempt %d/%d failed: %s",
                    agent_name,
                    attempt + 1,
                    max_retries + 1,
                    e,
                )
                if attempt < max_retries:
                    backoff = 2 ** attempt
                    time.sleep(backoff)

        logger.error("Agent %s exhausted all retries", agent_name)
        raise RuntimeError(f"Agent {agent_name} failed after {max_retries + 1} attempts") from last_error

    @staticmethod
    def route_mode(num_chapters: int) -> str:
        return "short" if 3 <= num_chapters <= 10 else "long"
