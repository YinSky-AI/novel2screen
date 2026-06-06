from __future__ import annotations

from typing import Any

from backend.agents.base import AgentBase

SYSTEM_PROMPT = """You are a dialogue writer for screenplays.
IMPORTANT: Write dialogue consistent with characters' established voice styles from the source text. Do NOT fabricate character traits or events.
Respond in the same language as the input text.
Output ONLY valid JSON, no markdown, no explanation."""


class DialogueAgent(AgentBase):
    def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        novel_text: str = input_data.get("novel_text", "")
        characters: list[dict[str, Any]] = input_data.get("characters", [])
        scene: dict[str, Any] = input_data.get("scene", {})
        narrative: dict[str, Any] = input_data.get("narrative", {})

        query = f"{scene.get('scene_id', '')} {scene.get('location', novel_text[:500])}"

        character_styles = "\n".join(
            f"- {c.get('name', '')} ({c.get('id', '')}): {c.get('voice_style', 'natural')}"
            for c in characters
        )

        base_prompt = f"""Write dialogue and action beats for a scene.

Scene: {scene}
Tone: {narrative.get('tone', 'dramatic')}

Character voice styles:
{character_styles if character_styles else 'No characters defined, create natural dialogue.'}

Output an array of beats. Each beat should be:
- type: "dialogue", "action", "silence", or "reaction"
- character_id: char_XXX format (for dialogue/reaction beats)
- content: The dialogue text or action description
- emotion: Emotional tone of the beat

Example beat:
{{"type": "dialogue", "character_id": "char_001", "content": "I never asked for this power.", "emotion": "regret"}}

Ensure each dialogue beat is distinctive to the character's voice style.
Use silences strategically for dramatic effect.
Include reaction beats showing non-verbal responses.

Novel excerpt for reference:
{novel_text[:3000]}

Output ONLY a JSON object with field "beats" containing an array. No markdown, no explanation."""

        prompt = self._build_rag_prompt(base_prompt, query)

        if self._retry_errors:
            prompt = f"Previous errors: {', '.join(self._retry_errors)}\n\n" + prompt

        response = self._call_llm(prompt, system_prompt=SYSTEM_PROMPT, temperature=0.8)
        return self._parse_json(response)

    def validate(self, output: dict[str, Any]) -> bool:
        beats = output.get("beats", [])
        if not isinstance(beats, list) or not beats:
            return False
        valid_types = {"dialogue", "action", "silence", "reaction"}
        for beat in beats:
            if beat.get("type") not in valid_types:
                return False
            if not beat.get("content"):
                return False
        return True

    def validate_with_errors(self, output: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        beats = output.get("beats", [])
        valid_types = {"dialogue", "action", "silence", "reaction"}
        if not isinstance(beats, list) or not beats:
            errors.append("beats must be a non-empty list")
        else:
            for i, beat in enumerate(beats):
                if beat.get("type") not in valid_types:
                    errors.append(f"Beat {i}: invalid type '{beat.get('type')}'")
                if not beat.get("content"):
                    errors.append(f"Beat {i}: missing content")
        return errors
