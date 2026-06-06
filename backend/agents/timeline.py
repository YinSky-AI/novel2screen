from __future__ import annotations

from typing import Any

from backend.agents.base import AgentBase

SYSTEM_PROMPT = """You are a story timeline analyst for screenplay adaptation.
IMPORTANT: Only include events explicitly described in the text. Do NOT fabricate any events, characters, or locations.
Respond in the same language as the input text.
Output ONLY valid JSON, no markdown, no explanation."""


class TimelineAgent(AgentBase):
    def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        novel_text: str = input_data.get("novel_text", "")
        characters: list[dict[str, Any]] = input_data.get("characters", [])
        narrative: dict[str, Any] = input_data.get("narrative", {})

        query = novel_text[:3000]

        character_names = [c.get("name", "") for c in characters]

        base_prompt = f"""Analyze the novel excerpt and create a timeline of events for screenplay adaptation.

Characters: {', '.join(character_names) if character_names else 'Extract from text'}
Narrative context: {narrative}

Output:
1. **events**: Array of timeline events, each with:
   - order: Integer sequence number
   - description: What happens
   - characters_involved: Array of character names
   - location: Where it happens
   - emotional_beat: The emotional significance
   - estimated_screen_time: Minutes estimate
2. **timeline_type**: "linear", "non-linear", or "branching"
3. **major_turning_points**: Array of key plot twist descriptions

Novel excerpt:
{novel_text[:5000]}

Output ONLY a JSON object. No markdown, no explanation."""

        prompt = self._build_rag_prompt(base_prompt, query)

        if self._retry_errors:
            prompt = f"Previous errors: {', '.join(self._retry_errors)}\n\n" + prompt

        response = self._call_llm(prompt, system_prompt=SYSTEM_PROMPT, temperature=0.5)
        return self._parse_json(response)

    def validate(self, output: dict[str, Any]) -> bool:
        events = output.get("events", [])
        return isinstance(events, list) and len(events) > 0

    def validate_with_errors(self, output: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        events = output.get("events", [])
        if not isinstance(events, list):
            errors.append("events must be a list")
        elif not events:
            errors.append("No events in timeline")
        else:
            for i, e in enumerate(events):
                if not e.get("description"):
                    errors.append(f"Event {i} missing description")
        if output.get("timeline_type") not in ("linear", "non-linear", "branching", ""):
            errors.append(f"Invalid timeline_type: {output.get('timeline_type')}")
        return errors
