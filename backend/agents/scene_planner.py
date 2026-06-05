"""
ScenePlannerAgent - Plans individual scenes for each episode.
"""
import json
from .base import AgentBase
from ..core.llm import llm_client
from ..core.prompts import SCENE_PLANNER_SYSTEM, SCENE_PLANNER_USER
from ..schemas.models import ScenePlan


class ScenePlannerAgent(AgentBase):
    """Plans individual scenes for each episode."""

    def __init__(self, model: str = "gpt-4o-mini"):
        super().__init__(name="ScenePlannerAgent", model=model)

    def run(self, input_data: dict) -> dict:
        response = llm_client.complete(
            system_prompt=SCENE_PLANNER_SYSTEM,
            user_prompt=SCENE_PLANNER_USER.format(
                episode_id=input_data.get("episode_id", ""),
                episode_title=input_data.get("episode_title", ""),
                episode_summary=input_data.get("episode_summary", ""),
                characters=json.dumps(input_data.get("characters", []), ensure_ascii=False),
                world_context=json.dumps(input_data.get("world_context", {}), ensure_ascii=False),
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
            ScenePlan(**output)
            return len(output.get("scenes", [])) >= 1
        except Exception:
            return False
