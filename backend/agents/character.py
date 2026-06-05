"""
CharacterAgent - Extracts character profiles from novel content.
"""
import json
from .base import AgentBase
from ..core.llm import llm_client
from ..core.prompts import CHARACTER_SYSTEM, CHARACTER_USER
from ..schemas.models import CharacterOutput


class CharacterAgent(AgentBase):
    """Extracts character profiles including goals, fears, arcs, and voice styles."""

    def __init__(self, model: str = "gpt-4o-mini"):
        super().__init__(name="CharacterAgent", model=model)

    def run(self, input_data: dict) -> dict:
        content = input_data.get("content", "")
        if not content:
            content = "\n\n".join(input_data.get("chunks", []))

        response = llm_client.complete(
            system_prompt=CHARACTER_SYSTEM,
            user_prompt=CHARACTER_USER.format(content=content),
            model=self.model,
            temperature=0.2,
        )

        return self._parse_response(response)


    def _parse_response(self, text: str) -> dict:
        import re
        text = text.strip()
        text = re.sub(r'`(?:json)?\s*', '', text)
        text = re.sub(r'\s*`', '', text)
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group())
            raise

    def validate(self, output: dict) -> bool:
        try:
            CharacterOutput(**output)
            return len(output.get("characters", [])) >= 1
        except Exception:
            return False
