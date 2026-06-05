"""DialogueAgent - Writes full screenplay dialogue with beats."""
import json

from ..core.llm import llm_client
from ..core.prompts import DIALOGUE_SYSTEM, DIALOGUE_USER
from ..schemas.models import Scene
from .base import AgentBase


class DialogueAgent(AgentBase):
    """Writes screenplay dialogue adhering to character voice styles."""

    def __init__(self, model: str = "gpt-4o-mini"):
        super().__init__(name="DialogueAgent", model=model)

    def run(self, input_data: dict) -> dict:
        response = llm_client.complete(
            system_prompt=DIALOGUE_SYSTEM,
            user_prompt=DIALOGUE_USER.format(
                scene_plan=json.dumps(input_data.get("scene_plan", {}), ensure_ascii=False),
                characters=json.dumps(input_data.get("characters", []), ensure_ascii=False),
            ),
            model=self.model,
            temperature=0.4,
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
            Scene(**output)
            return len(output.get("beats", [])) >= 2
        except Exception:
            return False
