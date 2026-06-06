from __future__ import annotations

from typing import Any

from backend.agents.base import AgentBase


class CriticAgent(AgentBase):
    def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        yaml_content: str = input_data.get("yaml_content", "")
        original_text: str = input_data.get("original_text", "")
        characters: list[dict[str, Any]] = input_data.get("characters", [])

        query = yaml_content[:3000]
        system_prompt = "You are a screenplay quality critic. Output valid JSON only."

        char_names = [c.get("name", "?") for c in characters]

        base_prompt = f"""Review the following screenplay YAML and provide a quality assessment.

Score each category 0-10 and identify issues:

1. **score**: Overall quality score (0-10)
2. **issues**: Array of objects with:
   - severity: "critical", "major", "minor"
   - category: e.g. "structure", "dialogue", "character", "pacing", "consistency"
   - description: What's wrong
   - location: Scene/episode reference
   - suggestion: How to fix
3. **suggestions**: Array of actionable improvement suggestions
4. **overall_assessment**: A paragraph summarizing overall quality

Characters: {', '.join(char_names) if char_names else 'Not provided'}
Original text snippet: {original_text[:2000]}

Screenplay YAML:
{yaml_content[:8000]}

Output ONLY a JSON object. No markdown, no explanation."""

        prompt = self._build_rag_prompt(base_prompt, query)

        if self._retry_errors:
            prompt = f"Previous errors: {', '.join(self._retry_errors)}\n\n" + prompt

        response = self._call_llm(prompt, system_prompt=system_prompt, temperature=0.4)
        return self._parse_json(response)

    def validate(self, output: dict[str, Any]) -> bool:
        has_score = "score" in output and isinstance(output["score"], (int, float))
        has_issues = isinstance(output.get("issues"), list)
        return has_score and has_issues

    def validate_with_errors(self, output: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        if "score" not in output:
            errors.append("Missing score field")
        elif not isinstance(output["score"], (int, float)):
            errors.append("score must be a number")
        if not isinstance(output.get("issues"), list):
            errors.append("issues must be a list")
        if not output.get("overall_assessment"):
            errors.append("overall_assessment is missing")
        return errors
