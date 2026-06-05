"""TimelineAgent - Organizes events into a timeline (linear for short, graph for long)."""
import json

from ..core.llm import llm_client
from ..core.prompts import TIMELINE_SYSTEM, TIMELINE_USER_LONG, TIMELINE_USER_SHORT
from ..schemas.models import TimelineOutput
from .base import AgentBase


class TimelineAgent(AgentBase):
    """Creates a chronological timeline of events."""

    def __init__(self, model: str = "gpt-4o-mini"):
        super().__init__(name="TimelineAgent", model=model)

    def run(self, input_data: dict) -> dict:
        events = input_data.get("major_events", [])
        mode = input_data.get("mode", "short")
        events_text = json.dumps(events, indent=2, ensure_ascii=False)

        if mode == "long":
            prompt = TIMELINE_USER_LONG.format(events=events_text)
        else:
            prompt = TIMELINE_USER_SHORT.format(events=events_text)

        response = llm_client.complete(
            system_prompt=TIMELINE_SYSTEM,
            user_prompt=prompt,
            model=self.model,
            temperature=0.2,
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
            TimelineOutput(**output)
            return len(output.get("events", [])) >= 1
        except Exception:
            return False
