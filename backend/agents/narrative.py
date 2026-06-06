from __future__ import annotations

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

        base_prompt = f"""Analyze the following novel excerpt and extract the narrative structure:

1. **title**: A compelling screenplay title
2. **logline**: A one-sentence summary — be specific, not generic
3. **genre**: Primary genre (e.g. sci-fi, fantasy, thriller, drama, romance)
4. **theme**: The central theme or message
5. **major_events**: Array of objects, each with:
   - chapter: Chapter number or label (use "ch_001" format if numbering)
   - event: Description of the major event
   - characters_involved: Array of character names present at this event
6. **subplots**: Array of strings describing secondary storylines

CONSTRAINTS:
- Do NOT invent characters, events, or locations that do not appear in the text. Only extract what is explicitly present.
- Keep the logline to one sentence. Be specific, not generic.

Novel excerpt:
{novel_text[:5000]}

Output ONLY a JSON object with these fields. No markdown, no explanation."""

        prompt = self._build_rag_prompt(base_prompt, query)

        if self._retry_errors:
            retry_context = f"You previously produced invalid output with these errors: {', '.join(self._retry_errors)}. Please correct them."
            prompt = retry_context + "\n\n" + prompt

        response = self._call_llm(prompt, system_prompt=SYSTEM_PROMPT, temperature=0.5)
        return self._parse_json(response)

    def validate(self, output: dict[str, Any]) -> bool:
        required = ["title", "logline", "genre", "theme", "major_events"]
        return all(k in output and output[k] for k in required)

    def validate_with_errors(self, output: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        required = ["title", "logline", "genre", "theme", "major_events"]
        for key in required:
            if key not in output or not output[key]:
                errors.append(f"Missing or empty required field: {key}")
        if "title" in output and len(str(output.get("title", ""))) < 2:
            errors.append("Title is too short")
        if "major_events" in output and not isinstance(output.get("major_events"), list):
            errors.append("major_events must be a list")
        return errors
