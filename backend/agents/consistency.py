from __future__ import annotations

from typing import Any

from backend.agents.base import AgentBase


class ConsistencyAgent(AgentBase):
    def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        original_chunks: list[str] = input_data.get("original_chunks", [])
        edited_yaml: str = input_data.get("edited_yaml", "")
        original_text: str = input_data.get("original_text", "")

        query = edited_yaml[:3000]
        system_prompt = "You are a consistency validator for novel-to-screen adaptations. Output valid JSON only."

        original_sample = "\n---\n".join(c[:500] for c in original_chunks[:5])

        base_prompt = f"""Compare the edited screenplay YAML against the original novel text and check for consistency issues:

1. Are characters present in the screenplay that do NOT exist in the original novel? (fabricated characters)
2. Are locations or settings mentioned that don't exist in the source material?
3. Do character personality traits or arcs deviate significantly from the source?
4. Are major plot events altered or missing?
5. Is tonal consistency maintained?

Original novel chunks (for reference):
{original_sample if original_sample else original_text[:3000]}

Edited screenplay YAML:
{edited_yaml[:8000]}

Output ONLY a JSON object with:
- **consistent**: boolean - true if no issues found
- **issues**: Array of objects: {{severity: "critical"/"major"/"minor", aspect: "character"/"plot"/"location"/"tone", description: str, source_reference: str, screenplay_reference: str}}
- **resolved**: boolean - true if all issues from previous run are resolved

No markdown, no explanation."""

        prompt = self._build_rag_prompt(base_prompt, query)

        if self._retry_errors:
            prompt = f"Previous errors: {', '.join(self._retry_errors)}\n\n" + prompt

        response = self._call_llm(prompt, system_prompt=system_prompt, temperature=0.3)
        return self._parse_json(response)

    def validate(self, output: dict[str, Any]) -> bool:
        return "consistent" in output and isinstance(output.get("issues"), list)

    def validate_with_errors(self, output: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        if "consistent" not in output:
            errors.append("Missing consistent field")
        if not isinstance(output.get("issues"), list):
            errors.append("issues must be a list")
        return errors
