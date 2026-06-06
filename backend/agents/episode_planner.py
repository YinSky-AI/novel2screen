from __future__ import annotations

from typing import Any

from backend.agents.base import AgentBase

SYSTEM_PROMPT = """You are an episode planner for TV series adaptation.
IMPORTANT: Base all episodes on events and characters explicitly present in the source text. Do NOT fabricate events.
Respond in the same language as the input text.
Output ONLY valid JSON, no markdown, no explanation."""


class EpisodePlannerAgent(AgentBase):
    def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        novel_text: str = input_data.get("novel_text", "")
        timeline: dict[str, Any] = input_data.get("timeline", {})
        narrative: dict[str, Any] = input_data.get("narrative", {})
        target_episodes: int = input_data.get("target_episodes", 10)

        query = novel_text[:3000]

        base_prompt = f"""Plan a TV series adaptation with approximately {target_episodes} episodes.

Timeline events: {timeline.get('events', [])}
Narrative: {narrative}

For each episode, provide:
- id: Format ep_NNN (e.g. ep_001, ep_002)
- title: Episode title
- summary: 2-3 sentence summary
- key_events: Array of event descriptions covered
- characters_featured: Array of character names appearing
- emotional_arc: The emotional journey of this episode
- cliffhanger: Optional cliffhanger at episode end

Also provide:
- **season_arc**: Description of the overall season arc

Novel excerpt for reference:
{novel_text[:3000]}

Output ONLY a JSON object with fields "episodes" (array) and "season_arc" (string). No markdown, no explanation."""

        prompt = self._build_rag_prompt(base_prompt, query)

        if self._retry_errors:
            prompt = f"Previous errors: {', '.join(self._retry_errors)}\n\n" + prompt

        response = self._call_llm(prompt, system_prompt=SYSTEM_PROMPT, temperature=0.6)
        return self._parse_json(response)

    def validate(self, output: dict[str, Any]) -> bool:
        episodes = output.get("episodes", [])
        return isinstance(episodes, list) and len(episodes) > 0 and "season_arc" in output

    def validate_with_errors(self, output: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        episodes = output.get("episodes", [])
        if not isinstance(episodes, list) or not episodes:
            errors.append("episodes must be a non-empty list")
        else:
            for i, ep in enumerate(episodes):
                if not ep.get("id") or not ep.get("title") or not ep.get("summary"):
                    errors.append(f"Episode {i} missing id/title/summary")
        if not output.get("season_arc"):
            errors.append("season_arc is missing")
        return errors
