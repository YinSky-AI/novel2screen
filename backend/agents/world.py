"""WorldAgent - Extracts world-building elements. Used in long mode only."""
import json

from ..core.llm import llm_client
from ..core.prompts import WORLD_SYSTEM, WORLD_USER
from ..schemas.models import WorldOutput
from .base import AgentBase


class WorldAgent(AgentBase):
    """Extracts world rules, magic systems, technology, politics, and geography."""

    def __init__(self, model: str = "gpt-4o-mini"):
        super().__init__(name="WorldAgent", model=model)

    def run(self, input_data: dict) -> dict:
        content = input_data.get("content", "")
        if not content:
            content = "\n\n".join(input_data.get("chunks", []))

        response = llm_client.complete(
            system_prompt=WORLD_SYSTEM,
            user_prompt=WORLD_USER.format(content=content),
            model=self.model,
            temperature=0.3,
        )

        return self._parse_response(response)


    def _parse_response(self, text: str) -> dict:
        import re
        text = text.strip()
        text = re.sub(r"`(?:json)?\s*", "", text)
        text = re.sub(r"\s*`", "", text)
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                return json.loads(match.group())
            raise

    def validate(self, output: dict) -> bool:
        try:
            WorldOutput(**output)
            return True
        except Exception:
            return False

    def get_default_context(self) -> dict:
        """Return default world context for short mode."""
        return {
            "world_rules": [{"domain": "general", "description": "Real-world setting with no supernatural elements"}],
            "geography": [],
        }
