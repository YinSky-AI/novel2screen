from __future__ import annotations

from typing import Any

from backend.agents.base import AgentBase


class WorldAgent(AgentBase):
    def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        novel_text: str = input_data.get("novel_text", "")

        query = novel_text[:3000]
        system_prompt = "You are a world-building specialist for screen adaptations. Output valid JSON only."

        base_prompt = f"""Analyze the following novel excerpt and extract world-building details:

1. **locations**: Array of objects, each with:
   - name: Location name
   - description: What the location looks and feels like
   - significance: Why this location matters to the story
   - visual_suggestions: How to film this location
2. **world_rules**: Array of objects describing special rules, magic systems, technology, or social norms:
   - rule: The rule or system
   - implications: How it affects the story
   - visual_representation: How to show it on screen
3. **atmosphere**: Overall world atmosphere

Novel excerpt:
{novel_text[:5000]}

Output ONLY a JSON object. No markdown, no explanation."""

        prompt = self._build_rag_prompt(base_prompt, query)

        if self._retry_errors:
            prompt = f"Previous errors: {', '.join(self._retry_errors)}\n\n" + prompt

        response = self._call_llm(prompt, system_prompt=system_prompt, temperature=0.5)
        return self._parse_json(response)

    def validate(self, output: dict[str, Any]) -> bool:
        has_locations = isinstance(output.get("locations"), list) and len(output["locations"]) > 0
        has_rules = isinstance(output.get("world_rules"), list)
        return has_locations or has_rules

    def validate_with_errors(self, output: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        if not isinstance(output.get("locations"), list):
            errors.append("locations must be a list")
        if not isinstance(output.get("world_rules"), list):
            errors.append("world_rules must be a list")
        if not output.get("locations") and not output.get("world_rules"):
            errors.append("At least locations or world_rules must be non-empty")
        return errors
