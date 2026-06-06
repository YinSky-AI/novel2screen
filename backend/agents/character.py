from __future__ import annotations

from typing import Any

from backend.agents.base import AgentBase

SYSTEM_PROMPT = """You are a character analyst. Extract ALL characters from the novel text.
IMPORTANT: Only include characters explicitly named in the text. Do NOT fabricate any characters.
For each character provide: id (char_001 format), name, role (protagonist/antagonist/supporting), goal, fear, arc, voice_style.
Respond in the same language as the input text.
Output ONLY valid JSON with a "characters" array."""


class CharacterAgent(AgentBase):
    def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        novel_text: str = input_data.get("novel_text", "")
        language: str = input_data.get("language", "auto")
        existing_characters: list[dict[str, Any]] = input_data.get("existing_characters", [])

        query = novel_text[:3000]
        characters_hint = ""
        if existing_characters:
            characters_hint = f"\n\nExisting characters to expand upon:\n{existing_characters}"

        base_prompt = f"""Analyze the following novel excerpt and identify all characters. For each character, provide:

- id: Use format char_001, char_002, etc. Start counting from {(len(existing_characters) + 1):03d}
- name: Character's full name
- role: One of "protagonist", "antagonist", "supporting"
- goal: What the character wants
- fear: What the character is afraid of (empty string if unknown)
- arc: The character's development journey
- voice_style: How they speak (e.g. formal, casual, sarcastic, terse)
{characters_hint}

Novel excerpt:
{novel_text[:5000]}

Output ONLY a JSON object with field "characters" containing an array. No markdown, no explanation."""

        prompt = self._build_rag_prompt(base_prompt, query)

        if self._retry_errors:
            prompt = f"Previous errors: {', '.join(self._retry_errors)}\n\n" + prompt

        response = self._call_llm(prompt, system_prompt=SYSTEM_PROMPT, temperature=0.5)
        return self._parse_json(response)

    def validate(self, output: dict[str, Any]) -> bool:
        characters = output.get("characters", [])
        if not isinstance(characters, list) or not characters:
            return False
        for c in characters:
            if not all(k in c for k in ["id", "name", "role", "goal", "arc"]):
                return False
        return True

    def validate_with_errors(self, output: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        characters = output.get("characters", [])
        if not isinstance(characters, list):
            errors.append("characters must be a list")
        elif not characters:
            errors.append("No characters extracted")
        else:
            for i, c in enumerate(characters):
                for field in ["id", "name", "role", "goal", "arc"]:
                    if field not in c or not c[field]:
                        errors.append(f"Character {i} missing field: {field}")
                if "id" in c and not c["id"].startswith("char_"):
                    errors.append(f"Character {i} has invalid id format: {c['id']}")
        return errors
