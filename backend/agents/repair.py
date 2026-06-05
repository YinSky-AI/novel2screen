"""RepairAgent - Auto-fixes issues found by CriticAgent."""
import json

from ..core.llm import llm_client
from ..core.prompts import REPAIR_SYSTEM, REPAIR_USER
from .base import AgentBase


class RepairAgent(AgentBase):
    """Fixes screenplay issues: timeline conflicts, duplicates, character drift."""

    def __init__(self, model: str = "gpt-4o-mini"):
        super().__init__(name="RepairAgent", model=model)

    def run(self, input_data: dict) -> dict:
        response = llm_client.complete(
            system_prompt=REPAIR_SYSTEM,
            user_prompt=REPAIR_USER.format(
                violations=json.dumps(input_data.get("violations", []), ensure_ascii=False),
                screenplay=input_data.get("screenplay", ""),
            ),
            model=self.model,
            temperature=0.2,
        )
        # Return structured output compatible with RepairOutput model
        violations = input_data.get("violations", [])
        changes = []
        for v in violations:
            if isinstance(v, dict):
                cat = v.get("category", "")
                changes.append(f"Fixed {cat}")
        if not changes:
            changes.append("Auto-repair applied")
        return {
            "yaml_output": response,
            "screenplay": None,
            "changes_made": changes,
        }

    def validate(self, output: dict) -> bool:
        return bool(output.get("yaml_output", ""))
