"""
CriticAgent - Reviews screenplay quality and consistency.
"""
import json
from .base import AgentBase
from ..core.llm import llm_client
from ..core.prompts import CRITIC_SYSTEM, CRITIC_USER
from ..schemas.models import CriticOutput


class CriticAgent(AgentBase):
    """Evaluates screenplay for continuity, pacing, character motivation, etc."""

    def __init__(self, model: str = "gpt-4o-mini"):
        super().__init__(name="CriticAgent", model=model)

    def run(self, input_data: dict) -> dict:
        response = llm_client.complete(
            system_prompt=CRITIC_SYSTEM,
            user_prompt=CRITIC_USER.format(
                screenplay=input_data.get("screenplay", ""),
            ),
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
            CriticOutput(**output)
            return True
        except Exception:
            return False

    def get_quality_score(self, output: dict) -> float:
        return output.get("score", 1.0)
