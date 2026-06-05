"""ModelRouter: cost-optimized LLM selection and retry with exponential backoff."""
from __future__ import annotations

import random
import time

from .llm import llm_client


class ModelRouter:
    """Routes agent tasks to optimal LLM models with retry logic."""

    MODEL_TABLE = {
        # Map per design doc ?13: use available models as fallbacks
        "narrative": "deepseek-chat",      # doc: claude-3-haiku
        "character": "deepseek-chat",      # doc: gpt-3.5-turbo
        "world": "deepseek-chat",          # doc: claude-3-sonnet (long mode)
        "timeline": "deepseek-chat",
        "episode_planner": "deepseek-chat",
        "scene_planner": "gpt-4o-mini",    # doc: gpt-4-turbo
        "dialogue": "deepseek-chat",       # doc: claude-3-haiku
        "yaml_compiler": "gpt-4o-mini",    # doc: gpt-4-turbo
        "critic": "gpt-4o-mini",           # doc: gpt-4-turbo
        "repair": "deepseek-chat",         # doc: gpt-3.5-turbo
        "consistency": "gpt-4o-mini",
    }

    def __init__(self, overrides: dict | None = None):
        if overrides:
            self.MODEL_TABLE.update(overrides)

    def get_model(self, agent_name: str) -> str:
        """Get the recommended model for an agent."""
        return self.MODEL_TABLE.get(agent_name, "deepseek-chat")

    def execute(self, agent_name: str, system_prompt: str, user_prompt: str,
                temperature: float = 0.3, max_retries: int = 2) -> str:
        """Execute an LLM call with model routing and exponential backoff."""
        model = self.get_model(agent_name)
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                return llm_client.complete(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model=model,
                    temperature=temperature,
                )
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    delay = (2 ** attempt) + random.uniform(0, 0.5)
                    time.sleep(delay)

        msg = f"{agent_name}: all {max_retries+1} retries failed. Last error: {last_error}"
        raise RuntimeError(msg)
