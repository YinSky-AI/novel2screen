from __future__ import annotations

from typing import Any

from backend.agents.base import AgentBase

SYSTEM_PROMPT = """You are a scene planner for screenplays.
IMPORTANT: Base all scenes on content explicitly present in the source text. Do NOT fabricate scenes, characters, or locations.
Respond in the same language as the input text.
Output ONLY valid JSON, no markdown, no explanation."""


class ScenePlannerAgent(AgentBase):
    def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        novel_text: str = input_data.get("novel_text", "")
        episodes: list[dict[str, Any]] = input_data.get("episodes", [])
        characters: list[dict[str, Any]] = input_data.get("characters", [])
        world: dict[str, Any] = input_data.get("world", {})

        episode_id = input_data.get("current_episode_id", episodes[0]["id"] if episodes else "ep_001")
        episode_data = next((ep for ep in episodes if ep.get("id") == episode_id), episodes[0]) if episodes else {}

        query = f"{episode_data.get('summary', novel_text[:1000])}"

        character_list = [f"{c.get('name', '')} (id: {c.get('id', '')})" for c in characters]
        known_locations = [loc.get("name", "") for loc in world.get("locations", [])]

        base_prompt = f"""Plan individual scenes for episode: {episode_data}

Characters: {', '.join(character_list) if character_list else 'Extract from text'}
Known locations: {', '.join(known_locations) if known_locations else 'Extract from text'}

For each scene, provide:
- scene_id: Format sc_NNN (e.g. sc_001), start counting sequentially from the first scene across all episodes
   Current episode is {episode_id}, suggesting IDs start from the episode's position
- location: Where the scene takes place
- time: Time of day / context
- visual_focus: What the camera should focus on
- sound_effect: Key sound design element if any
- voice_over: Voice over text if any
- transition: One of "cut", "fade", "dissolve", "wipe" (default "cut")
- duration_estimate: Estimated seconds (typically 60-180)
- beats: Array of beat objects, each containing:
    - type: One of "dialogue", "action", "silence", "reaction"
    - character_id: char_XXX format of speaking/acting character
    - content: The dialogue or action description
    - emotion: Emotional tone

Target 3-6 scenes per episode.

Novel context:
{novel_text[:3000]}

Output ONLY a JSON object with fields "episode_id" (string) and "scenes" (array). No markdown, no explanation."""

        prompt = self._build_rag_prompt(base_prompt, query)

        if self._retry_errors:
            prompt = f"Previous errors: {', '.join(self._retry_errors)}\n\n" + prompt

        response = self._call_llm(prompt, system_prompt=SYSTEM_PROMPT, temperature=0.7)
        return self._parse_json(response)

    def validate(self, output: dict[str, Any]) -> bool:
        scenes = output.get("scenes", [])
        if not isinstance(scenes, list) or not scenes:
            return False
        for sc in scenes:
            if not sc.get("scene_id") or not sc.get("location"):
                return False
        return True

    def validate_with_errors(self, output: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        scenes = output.get("scenes", [])
        if not isinstance(scenes, list) or not scenes:
            errors.append("scenes must be a non-empty list")
        else:
            for i, sc in enumerate(scenes):
                if not sc.get("scene_id"):
                    errors.append(f"Scene {i} missing scene_id")
                if not sc.get("location"):
                    errors.append(f"Scene {i} ({sc.get('scene_id', '?')}) missing location")
        if not output.get("episode_id"):
            errors.append("episode_id is missing")
        return errors
