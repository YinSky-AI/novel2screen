"""
NarrativeAgent - Extracts narrative structure from novel chunks.
"""
import json
from typing import Any

from .base import AgentBase
from ..core.llm import llm_client
from ..core.prompts import NARRATIVE_SYSTEM, NARRATIVE_USER
from ..schemas.models import NarrativeOutput


class NarrativeAgent(AgentBase):
    """Extracts major events, subplots, turning points, and themes."""

    def __init__(self, model: str = "gpt-4o-mini"):
        super().__init__(name="NarrativeAgent", model=model)

    def run(self, input_data: dict) -> dict:
        chunks = input_data.get("chunks", [])
        chunks_text = "\n\n---CHAPTER BREAK---\n\n".join(
            f"Chapter {i+1}:\n{chunk}" for i, chunk in enumerate(chunks)
        )

        response = llm_client.complete(
            system_prompt=NARRATIVE_SYSTEM,
            user_prompt=NARRATIVE_USER.format(chunks=chunks_text),
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
            NarrativeOutput(**output)
            events = output.get("major_events", [])
            # Check coverage: at least some events extracted
            return len(events) >= 1
        except Exception:
            return False
