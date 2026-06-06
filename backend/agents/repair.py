from __future__ import annotations

from typing import Any

from backend.agents.base import AgentBase


class RepairAgent(AgentBase):
    def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        yaml_content: str = input_data.get("yaml_content", "")
        issues: list[dict[str, Any]] = input_data.get("issues", [])
        suggestions: list[str] = input_data.get("suggestions", [])
        original_text: str = input_data.get("original_text", "")

        query = yaml_content[:2000]
        system_prompt = "You are a screenplay repair specialist. Output valid JSON only."

        issues_text = "\n".join(
            f"- [{i.get('severity', '?')}] {i.get('category', '?')}: {i.get('description', '')}"
            for i in issues
        )
        suggestions_text = "\n".join(f"- {s}" for s in suggestions)

        base_prompt = f"""Repair the following screenplay YAML based on the identified issues and suggestions.

Issues found:
{issues_text if issues_text else 'No specific issues provided.'}

Suggestions:
{suggestions_text if suggestions_text else 'No specific suggestions provided.'}

Current YAML:
{yaml_content[:10000]}

Original text reference:
{original_text[:3000]}

Output ONLY a JSON object with:
- **repaired_yaml**: The full corrected YAML as a string
- **changes_made**: Array of objects describing each change: {{field, before, after, reason}}
- **validation_passed**: boolean indicating if the repair resolves all issues

Preserve the YAML structure exactly. Only fix identified problems.
Ensure all character IDs referenced exist in the character list.
Ensure all scene_ids are unique across episodes.
Ensure all transitions are valid (cut, fade, dissolve, wipe).
Ensure all beat types are valid (dialogue, action, silence, reaction).

No markdown, no explanation."""

        prompt = self._build_rag_prompt(base_prompt, query)

        if self._retry_errors:
            prompt = f"Previous errors: {', '.join(self._retry_errors)}\n\n" + prompt

        response = self._call_llm(prompt, system_prompt=system_prompt, temperature=0.3)
        return self._parse_json(response)

    def validate(self, output: dict[str, Any]) -> bool:
        return "repaired_yaml" in output and isinstance(output["repaired_yaml"], str) and len(output["repaired_yaml"]) > 10

    def validate_with_errors(self, output: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        if "repaired_yaml" not in output:
            errors.append("Missing repaired_yaml field")
        elif not isinstance(output["repaired_yaml"], str):
            errors.append("repaired_yaml must be a string")
        elif len(output["repaired_yaml"]) < 10:
            errors.append("repaired_yaml is too short")
        if not isinstance(output.get("changes_made"), list):
            errors.append("changes_made must be a list")
        if "validation_passed" not in output:
            errors.append("Missing validation_passed field")
        return errors
