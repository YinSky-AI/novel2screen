from __future__ import annotations

from typing import Any

from backend.agents.base import AgentBase


class NarrativeAgent(AgentBase):
    def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        novel_text: str = input_data.get("novel_text", "")
        query = novel_text[:3000]

        system_prompt = "You are a professional screenplay analyst. Output valid JSON only."
        base_prompt = f"""Analyze the following novel excerpt and extract the narrative structure:

1. **title**: A compelling screenplay title
2. **logline**: A one-sentence summary (1-2 sentences max)
3. **genre**: Primary genre (e.g. sci-fi, fantasy, thriller, drama, romance)
4. **theme**: The central theme or message
5. **core_conflict**: The main conflict driving the story
6. **tone**: The overall tone (e.g. dark, hopeful, satirical)
7. **target_audience**: Suggested target audience
8. **style_notes**: Visual or narrative style suggestions

Novel excerpt:
{novel_text[:5000]}

Output ONLY a JSON object with these fields. No markdown, no explanation."""

        prompt = self._build_rag_prompt(base_prompt, query)

        if self._retry_errors:
            retry_context = f"You previously produced invalid output with these errors: {', '.join(self._retry_errors)}. Please correct them."
            prompt = retry_context + "\n\n" + prompt

        response = self._call_llm(prompt, system_prompt=system_prompt, temperature=0.5)
        return self._parse_json(response)

    def validate(self, output: dict[str, Any]) -> bool:
        required = ["title", "logline", "genre", "theme", "core_conflict"]
        return all(k in output and output[k] for k in required)

    def validate_with_errors(self, output: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        required = ["title", "logline", "genre", "theme", "core_conflict"]
        for key in required:
            if key not in output or not output[key]:
                errors.append(f"Missing or empty required field: {key}")
        if "title" in output and len(str(output.get("title", ""))) < 2:
            errors.append("Title is too short")
        return errors
