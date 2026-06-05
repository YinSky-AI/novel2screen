"""
LLM client abstraction for Novel2Screen.
Supports OpenAI and Anthropic models with demo mode fallback.
"""
from __future__ import annotations
import json
from ..config import OPENAI_API_KEY, ANTHROPIC_API_KEY, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL


class LLMClient:
    """Unified LLM client with demo mode fallback."""

    def __init__(self):
        self._openai_client = None
        self._anthropic_client = None
        self._deepseek_client = None

    def _get_openai(self):
        if self._openai_client is None and OPENAI_API_KEY:
            from openai import OpenAI
            self._openai_client = OpenAI(api_key=OPENAI_API_KEY)
        return self._openai_client


    def _get_deepseek(self):
        if self._deepseek_client is None and DEEPSEEK_API_KEY:
            from openai import OpenAI
            self._deepseek_client = OpenAI(
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_BASE_URL
            )
        return self._deepseek_client

    def _get_anthropic(self):
        if self._anthropic_client is None and ANTHROPIC_API_KEY:
            import anthropic
            self._anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        return self._anthropic_client

    def complete(self, system_prompt, user_prompt, model=None, temperature=0.3, response_format=None):
        """Send completion. Tries DeepSeek first, then falls back through providers to demo mode."""
        if model is None:
            model = "deepseek-chat"
        
        # 1. Try DeepSeek (OpenAI-compatible)
        client = self._get_deepseek()
        if client:
            try:
                resp = client.chat.completions.create(
                    model=DEEPSEEK_MODEL,  # Always use DeepSeek model
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=temperature,
                )
                return resp.choices[0].message.content or ""
            except Exception as e:
                # Fall through to next provider
                pass
        
        # 2. Try OpenAI
        client = self._get_openai()
        if client:
            try:
                resp = client.chat.completions.create(
                    model=model if model != "deepseek-chat" else "gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=temperature,
                )
                return resp.choices[0].message.content or ""
            except Exception:
                pass
        
        # 3. Try Anthropic
        client = self._get_anthropic()
        if client:
            try:
                resp = client.messages.create(
                    model="claude-3-haiku-20240307",
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                    temperature=temperature,
                    max_tokens=4096,
                )
                return resp.content[0].text if resp.content else ""
            except Exception:
                pass
        
        # 4. Demo mode fallback
        return self._demo_complete(system_prompt, user_prompt)


    def _demo_complete(self, system_prompt, user_prompt):
        """Generate demo output when no API keys configured."""
        up = user_prompt.lower()
        sp = system_prompt.lower()
        
        if 'timeline' in sp:
            return self._demo_timeline()
        elif 'dialogue' in sp:
            return self._demo_dialogue()
        elif 'character' in sp:
            return self._demo_characters()
        elif 'narrative' in sp:
            return self._demo_narrative()
        elif 'world' in sp:
            return self._demo_world()
        elif 'critic' in sp:
            return json.dumps({"violations": [], "score": 0.92})
        elif 'repair' in sp:
            return 'title: Repaired Screenplay\nlogline: Auto-fixed\nversion: 1'
        elif 'scene' in sp and 'dialogue' not in sp:
            return self._demo_scene_plan()
        elif 'episode' in sp:
            return self._demo_episode_plan()
        else:
            return '{"result": "demo output"}'

    def _demo_characters(self):
        import json
        return json.dumps({"characters": [
            {"id": "char_001", "name": "Lin Ye", "role": "protagonist", "goal": "Save the city", "fear": "Losing control", "arc": "Self-sacrifice to redemption", "voice_style": "calm and resolute"},
            {"id": "char_002", "name": "Su Wan", "role": "supporting", "goal": "Protect Lin Ye", "fear": "Losing him", "arc": "From fear to courage", "voice_style": "emotional and caring"},
            {"id": "char_003", "name": "Dr. Chen", "role": "supporting", "goal": "Stabilize the rift", "fear": "Scientific failure", "arc": "Observer to participant", "voice_style": "analytical and precise"}
        ]}, ensure_ascii=False)

    def _demo_narrative(self):
        import json
        return json.dumps({"major_events": [
            {"chapter": 1, "description": "Lin Ye stands atop a skyscraper overlooking the twilight city.", "characters_involved": ["Lin Ye"]},
            {"chapter": 2, "description": "Alarm at the institute. Rift expanding.", "characters_involved": ["Lin Ye", "Dr. Chen"]},
            {"chapter": 3, "description": "Lin Ye decides to use his powers despite pleas.", "characters_involved": ["Lin Ye", "Su Wan"]},
            {"chapter": 4, "description": "The rift closes. New light forms.", "characters_involved": ["Lin Ye", "Su Wan"]},
            {"chapter": 5, "description": "Team enters the dimensional gate.", "characters_involved": ["Lin Ye", "Su Wan", "Dr. Chen"]}
        ], "subplots": [{"name": "The Sacrifice Bond", "description": "Love tested by sacrifice"}],
        "turning_points": [{"chapter": 3, "description": "Lin Ye chooses sacrifice", "impact": "Climax"}],
        "theme": "Sacrifice and redemption"}, ensure_ascii=False)

    def _demo_world(self):
        import json
        return json.dumps({"world_rules": [
            {"domain": "magic", "description": "Dimensional energy at great cost"},
            {"domain": "technology", "description": "Advanced rift monitoring"}
        ], "geography": [{"name": "Twilight City", "description": "Neon metropolis", "significance": "Main setting"}]})

    def _demo_timeline(self):
        import json
        return json.dumps({"events": [
            {"chapter": 1, "description": "Establish setting"},
            {"chapter": 2, "description": "Inciting incident"},
            {"chapter": 3, "description": "Climax decision"},
            {"chapter": 4, "description": "Resolution"},
            {"chapter": 5, "description": "New beginning"}
        ]})

    def _demo_episode_plan(self):
        import json
        return json.dumps({"episodes": [
            {"id": "ep_001", "title": "The Twilight City", "summary": "Introduction and crisis"},
            {"id": "ep_002", "title": "The Choice", "summary": "The sacrifice decision"},
            {"id": "ep_003", "title": "New Horizon", "summary": "Aftermath and new world"}
        ]})

    def _demo_scene_plan(self):
        import json
        return json.dumps({"scenes": [
            {"scene_id": "sc_001", "location": "Rooftop", "time": "Night", "objective": "Establish", "conflict": "Man vs nature", "emotion": "Melancholic"},
            {"scene_id": "sc_002", "location": "Institute", "time": "Night", "objective": "Reveal crisis", "conflict": "Time pressure", "emotion": "Urgent"},
            {"scene_id": "sc_003", "location": "Rift Edge", "time": "Dawn", "objective": "Climax", "conflict": "Life vs duty", "emotion": "Tense"}
        ]})

    def _demo_dialogue(self):
        import json
        return json.dumps({"scene_id": "sc_001", "location": "Rooftop", "time": "Night",
            "visual_focus": "Lin Ye at the edge, city lights below",
            "beats": [
                {"type": "action", "content": "Lin Ye steps onto the rooftop.", "emotion": None},
                {"type": "dialogue", "character_id": "char_001", "content": "Three years since everything changed.", "emotion": "contemplative"},
                {"type": "action", "content": "He holds up the glowing chip.", "emotion": None}
            ], "transition": "fade", "duration_estimate": "120s"}, ensure_ascii=False)




    def _demo_characters(self):
        import json
        return json.dumps({"characters": [
            {"id": "char_001", "name": "Lin Ye", "role": "protagonist", "goal": "Save the city", "fear": "Losing control", "arc": "Self-sacrifice to redemption", "voice_style": "calm and resolute"},
            {"id": "char_002", "name": "Su Wan", "role": "supporting", "goal": "Protect Lin Ye", "fear": "Losing him", "arc": "From fear to courage", "voice_style": "emotional and caring"},
            {"id": "char_003", "name": "Dr. Chen", "role": "supporting", "goal": "Stabilize the rift", "fear": "Scientific failure", "arc": "Observer to participant", "voice_style": "analytical and precise"}
        ]}, ensure_ascii=False)

    def _demo_narrative(self):
        import json
        return json.dumps({"major_events": [
            {"chapter": 1, "description": "Lin Ye stands atop a skyscraper overlooking the twilight city, holding a blue-glowing chip.", "characters_involved": ["Lin Ye"]},
            {"chapter": 2, "description": "Alarm at the research institute - Dr. Chen detects the rift expanding.", "characters_involved": ["Lin Ye", "Dr. Chen"]},
            {"chapter": 3, "description": "Lin Ye decides to use his powers despite Su Wan plea.", "characters_involved": ["Lin Ye", "Su Wan"]},
            {"chapter": 4, "description": "The rift closes. Lin Ye collapses. A new light forms.", "characters_involved": ["Lin Ye", "Su Wan"]},
            {"chapter": 5, "description": "Three months later. The team enters the dimensional gate.", "characters_involved": ["Lin Ye", "Su Wan", "Dr. Chen"]}
        ], "subplots": [{"name": "The Sacrifice Bond", "description": "Lin Ye and Su Wan relationship tested", "related_characters": ["Lin Ye", "Su Wan"]}],
        "turning_points": [{"chapter": 3, "description": "Lin Ye chooses sacrifice", "impact": "Climax of character arc"}],
        "theme": "Sacrifice and redemption in the face of inevitable change"}, ensure_ascii=False)

    def _demo_world(self):
        import json
        return json.dumps({"world_rules": [
            {"domain": "magic", "description": "Dimensional energy can be harnessed at great cost"},
            {"domain": "technology", "description": "Advanced rift monitoring systems"}
        ], "geography": [{"name": "Twilight City", "description": "Neon metropolis rebuilt after crisis", "significance": "Main setting"}]})

    def _demo_timeline(self):
        import json
        return json.dumps({"events": [
            {"chapter": 1, "description": "Establishing the twilight city and rift"},
            {"chapter": 2, "description": "Rift instability detected at institute"},
            {"chapter": 3, "description": "Lin Ye defies Su Wan and uses his power"},
            {"chapter": 4, "description": "Rift closes, Lin Ye falls, new gate appears"},
            {"chapter": 5, "description": "Team enters the new world"}
        ]})

    def _demo_episode_plan(self):
        import json
        return json.dumps({"episodes": [
            {"id": "ep_001", "title": "The Twilight City", "summary": "Introduction to Lin Ye, the rift crisis, and the team"},
            {"id": "ep_002", "title": "The Choice", "summary": "The rift destabilizes. Lin Ye must choose."},
            {"id": "ep_003", "title": "New Horizon", "summary": "Aftermath and the gateway to a new dimension"}
        ]})

    def _demo_scene_plan(self):
        import json
        return json.dumps({"scenes": [
            {"scene_id": "sc_001", "location": "Rooftop", "time": "Night", "objective": "Establish setting", "conflict": "Man vs nature", "emotion": "Melancholic"},
            {"scene_id": "sc_002", "location": "Research Institute", "time": "Night", "objective": "Reveal crisis", "conflict": "Time pressure", "emotion": "Urgent"},
            {"scene_id": "sc_003", "location": "Rift Edge", "time": "Dawn", "objective": "Climax decision", "conflict": "Life vs duty", "emotion": "Tense"}
        ]})

    def _demo_dialogue(self):
        import json
        return json.dumps({"scene_id": "sc_001", "location": "Rooftop", "time": "Night",
            "visual_focus": "Lin Ye at the edge, city lights below",
            "beats": [
                {"type": "action", "content": "Lin Ye steps onto the rooftop. Wind catches his coat.", "emotion": None},
                {"type": "dialogue", "character_id": "char_001", "content": "Three years since everything changed.", "emotion": "contemplative"},
                {"type": "action", "content": "He holds up the glowing chip.", "emotion": None},
                {"type": "dialogue", "character_id": "char_003", "content": "The readings are off the charts.", "emotion": "urgent"},
                {"type": "dialogue", "character_id": "char_001", "content": "I have been ready for this.", "emotion": "resolute"}
            ], "transition": "fade", "duration_estimate": "120s"}, ensure_ascii=False)


# Global singleton
llm_client = LLMClient()
