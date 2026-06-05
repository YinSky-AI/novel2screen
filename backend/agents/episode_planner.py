"""
EpisodePlannerAgent - Plans episode structure from narrative analysis.
"""
import json
from .base import AgentBase
from ..core.llm import llm_client
from ..core.prompts import EPISODE_PLANNER_SYSTEM, EPISODE_PLANNER_USER
from ..schemas.models import EpisodePlan


class EpisodePlannerAgent(AgentBase):
    """Plans episode structure from narrative analysis."""

    def __init__(self, model: str = "gpt-4o-mini"):
        super().__init__(name="EpisodePlannerAgent", model=model)

    def run(self, input_data: dict) -> dict:
        response = llm_client.complete(
            system_prompt=EPISODE_PLANNER_SYSTEM,
            user_prompt=EPISODE_PLANNER_USER.format(
                narrative=json.dumps(input_data.get("narrative", {}), ensure_ascii=False),
                characters=json.dumps(input_data.get("characters", []), ensure_ascii=False),
                mode=input_data.get("mode", "short"),
            ),
            model=self.model,
            temperature=0.3,
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
            EpisodePlan(**output)
            return len(output.get("episodes", [])) >= 1
        except Exception:
            return False
