from __future__ import annotations

import json
from typing import Any

from backend.agents.base import AgentBase

SYSTEM_PROMPT = """You are a professional screenplay analyst. Extract narrative structure from novel text.
IMPORTANT: Respond in the same language as the input text.
Do NOT fabricate any characters, events, or locations not explicitly present in the text.
Output ONLY valid JSON, no markdown, no explanation."""


class NarrativeAgent(AgentBase):
    def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        novel_text: str = input_data.get("novel_text", "")
        query = novel_text[:3000]

        base_prompt = f"""Analyze the following novel excerpt. Output valid JSON with these fields:

1. "title": A compelling screenplay title
2. "logline": One specific sentence summarizing the story
3. "genre": Primary genre
4. "theme": Central theme
5. "major_events": Array of objects. For EACH event include:
   - "chapter": chapter number (int)
   - "event": what happens (str)
   - "location": EXACT location name from the text (e.g. "改装集装箱工作间", "server room B4"). NEVER use "Unknown".
   - "time": specific time from text (e.g. "Night", "Dawn", "Afternoon", "凌晨"). NEVER just "Day".
   - "characters_involved": list of character names present
   - "emotion": dominant emotion (e.g. "tension", "fear", "hope", "sadness", "anger")
   - "visual_focus": what the camera would see (e.g. "flickering LEDs", "steam rising from noodles")
   - "sound_effect": ambient or specific sounds (e.g. "distant hum", "keyboard clicking")
6. "subplots": Array of strings describing secondary storylines

CONSTRAINTS:
- Extract ONLY from the text. Do NOT invent anything.
- location and time MUST be specific — never generic like "Unknown" or "Day".
- visual_focus and sound_effect help build cinematic atmosphere.

Novel excerpt:
{novel_text[:5000]}

Output ONLY the JSON object, no markdown, no explanation."""

        prompt = self._build_rag_prompt(base_prompt, query)

        if self._retry_errors:
            retry_context = f"Previous errors: {', '.join(self._retry_errors)}. Fix them."
            prompt = retry_context + "\n\n" + prompt

        response = self._call_llm(prompt, system_prompt=SYSTEM_PROMPT, temperature=0.5)
        return self._parse_json(response)

    def validate(self, output: dict[str, Any]) -> bool:
        required = ["title", "logline", "genre", "theme", "major_events"]
        return all(k in output and output[k] for k in required)

    def validate_with_errors(self, output: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        required = ["title", "logline", "genre", "theme", "major_events"]
        for k in required:
            if k not in output or not output[k]:
                errors.append(f"Missing: {k}")
        if "major_events" in output:
            if not isinstance(output["major_events"], list):
                errors.append("major_events must be a list")
            else:
                for i, ev in enumerate(output["major_events"]):
                    if not isinstance(ev, dict):
                        errors.append(f"major_events[{i}] is not an object")
                    elif "event" not in ev or "location" not in ev:
                        errors.append(f"major_events[{i}] missing event or location")
        return errors
