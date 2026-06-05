"""ModelRouter: cost-optimized LLM selection and retry with exponential backoff."""
from __future__ import annotations
import time
import random
from typing import Optional
from .llm import llm_client


class ModelRouter:
    """Routes agent tasks to optimal LLM models with retry logic."""

    MODEL_TABLE = {
        "narrative": "deepseek-chat",
        "character": "deepseek-chat",
        "world": "deepseek-chat",
        "timeline": "deepseek-chat",
        "episode_planner": "deepseek-chat",
        "scene_planner": "gpt-4o-mini",
        "dialogue": "deepseek-chat",
        "yaml_compiler": "gpt-4o-mini",
        "critic": "deepseek-chat",
        "repair": "deepseek-chat",
        "consistency": "deepseek-chat",
    }

    def __init__(self, overrides: Optional[dict] = None):
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

        raise RuntimeError(f"{agent_name}: all {max_retries+1} retries failed. Last error: {last_error}")
