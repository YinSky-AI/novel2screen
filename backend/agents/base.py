"""
Agent base class for Novel2Screen.
Every agent implements run(), validate(), and retry().
"""
from abc import ABC, abstractmethod
from typing import Any, Callable
import time


class AgentError(Exception):
    """Base exception for agent failures."""
    pass


class AgentBase(ABC):
    """Abstract base class for all Novel2Screen agents."""

    def __init__(self, name: str, model: str = "", max_retries: int = 2):
        self.name = name
        self.model = model
        self.max_retries = max_retries
        self.attempt_count = 0
        try:
            from ..core.router import ModelRouter
            self.router = ModelRouter()
        except Exception:
            self.router = None

    @abstractmethod
    def run(self, input_data: dict) -> dict:
        """
        Execute the agent's core logic.
        Must return a dict conforming to the agent's output schema.
        """
        pass

    @abstractmethod
    def validate(self, output: dict) -> bool:
        """
        Validate the agent's output against its schema.
        Returns True if valid, False otherwise.
        """
        pass

    def retry(self, input_data: dict, validation_fn: Callable[[dict], bool] = None) -> dict:
        """
        Run the agent with retry logic.
        Re-runs up to max_retries if validation fails.
        """
        last_error = None
        for attempt in range(self.max_retries + 1):
            self.attempt_count = attempt + 1
            try:
                output = self.run(input_data)

                # Use instance validate() or provided validation_fn
                is_valid = (validation_fn or self.validate)(output)
                if is_valid:
                    return output

                last_error = f"Validation failed on attempt {attempt + 1}"
            except Exception as e:
                last_error = f"Error on attempt {attempt + 1}: {e}"

        raise AgentError(
            f"Agent '{self.name}' failed after {self.max_retries + 1} attempts. "
            f"Last error: {last_error}"
        )

    def get_llm_response(self, system_prompt: str, user_prompt: str,
                          temperature: float = 0.3) -> str:
        """Route LLM call through ModelRouter if available."""
        if self.router:
            agent_key = self.name.replace("Agent", "").lower()
            return self.router.execute(agent_key, system_prompt, user_prompt, temperature)
        from ..core.llm import llm_client
        return llm_client.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=self.model,
            temperature=temperature,
        )

    def get_attempt_count(self) -> int:
        return self.attempt_count
