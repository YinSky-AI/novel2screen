"""PromptLoader: reads prompt templates from YAML files in prompts/ directory."""
import os
import yaml
from typing import Optional


class PromptLoader:
    """Loads prompt templates from YAML files."""

    def __init__(self, prompts_dir: Optional[str] = None):
        self.prompts_dir = prompts_dir or os.path.join(
            os.path.dirname(__file__), "..", "prompts"
        )
        self._cache: dict[str, dict] = {}

    def load(self, agent_name: str) -> dict:
        """Load prompt template for an agent. Results are cached."""
        if agent_name in self._cache:
            return self._cache[agent_name]

        fpath = os.path.join(self.prompts_dir, f"{agent_name}.yaml")
        if not os.path.exists(fpath):
            raise FileNotFoundError(f"Prompt file not found: {fpath}")

        with open(fpath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self._cache[agent_name] = data
        return data

    def get_system(self, agent_name: str) -> str:
        return self.load(agent_name).get("system", "")

    def get_user_template(self, agent_name: str) -> str:
        return self.load(agent_name).get("user_template", "")
