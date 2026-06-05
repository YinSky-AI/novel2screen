"""LLM client abstraction for Novel2Screen.
Supports OpenAI and Anthropic models with demo mode fallback.
"""
from __future__ import annotations

import json

from ..config import ANTHROPIC_API_KEY, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, OPENAI_API_KEY


class LLMClient:
    """Unified LLM client with demo mode fallback."""

    def __init__(self):
        self._openai_client = None
        self._anthropic_client = None
        self._deepseek_client = None
        self.total_cost = 0.0
        self.total_tokens = 0
        self.call_count = 0
        self._ollama_base = "http://localhost:11434"

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
                base_url=DEEPSEEK_BASE_URL,
            )
        return self._deepseek_client

    def _get_anthropic(self):
        if self._anthropic_client is None and ANTHROPIC_API_KEY:
            import anthropic
            self._anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        return self._anthropic_client

    def complete(self, system_prompt, user_prompt, model=None, temperature=0.3, response_format=None):
        """Send completion. Tries: DeepSeek -> OpenAI -> Anthropic -> Ollama -> Demo."""
        if model is None:
            model = "deepseek-chat"

        try:
            from ..config import DEEPSEEK_MODEL as _MODEL
        except:
            _MODEL = "deepseek-chat"

        # 1. Try DeepSeek
        client = self._get_deepseek()
        if client:
            try:
                import os as _os2
                actual_model = _os2.getenv("DEEPSEEK_MODEL", "deepseek-chat")
                resp = client.chat.completions.create(
                    model=actual_model,
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                    temperature=temperature,
                )
                result = resp.choices[0].message.content or ""
                if resp.usage:
                    self._track_cost(actual_model, resp.usage.prompt_tokens, resp.usage.completion_tokens)
                return result
            except Exception:
                pass

        # 2. Try OpenAI
        client = self._get_openai()
        if client:
            try:
                m = "gpt-4o-mini" if model == "deepseek-chat" else model
                resp = client.chat.completions.create(
                    model=m,
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                    temperature=temperature,
                )
                result = resp.choices[0].message.content or ""
                if resp.usage:
                    self._track_cost(m, resp.usage.prompt_tokens, resp.usage.completion_tokens)
                return result
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
                result = resp.content[0].text if resp.content else ""
                if resp.usage:
                    self._track_cost("claude-3-haiku-20240307", resp.usage.input_tokens, resp.usage.output_tokens)
                return result
            except Exception:
                pass

        # 4. Try Ollama (local)
        try:
            ollama_result = self._call_ollama(system_prompt, user_prompt, temperature)
            if ollama_result:
                return ollama_result
        except Exception:
            pass

        # 5. Demo mode fallback
        return self._demo_complete(system_prompt, user_prompt)



    def _track_cost(self, model="", input_tokens=0, output_tokens=0, success=True) -> None:
        """Track token usage and cost."""
        if not success:
            return
        self.total_tokens += input_tokens + output_tokens
        self.call_count += 1
        MODEL_PRICES = {
            "deepseek-chat": {"input": 0.00014, "output": 0.00028},
            "gpt-4o-mini": {"input": 0.00015, "output": 0.00060},
        }
        prices = MODEL_PRICES.get(model, {"input": 0.0002, "output": 0.0004})
        cost = (input_tokens / 1000 * prices["input"]) + (output_tokens / 1000 * prices["output"])
        self.total_cost += cost

    def get_usage_report(self):
        """Return usage stats."""
        return {
            "total_cost_usd": round(self.total_cost, 4),
            "total_tokens": self.total_tokens,
            "call_count": self.call_count,
            "avg_cost_per_call": round(self.total_cost / max(self.call_count, 1), 6),
        }

    def _call_ollama(self, system_prompt, user_prompt, temperature=0.3):
        """Call local Ollama API."""
        import os as _os

        import requests
        try:
            base = _os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            model = _os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
            resp = requests.post(
                f"{base}/api/chat",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "options": {"temperature": temperature},
                    "stream": False,
                },
                timeout=120,
            )
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("message", {}).get("content", "")
                est_tokens = max(len(content) // 3, 1)
                self._track_cost("ollama-local", output_tokens=est_tokens, success=True)
                return content
            return ""
        except Exception:
            return ""


    def _demo_complete(self, system_prompt, user_prompt):
        """Generate demo output when no API keys configured."""
        user_prompt.lower()
        sp = system_prompt.lower()

        if "consistency" in sp:
            import json as _json
            return _json.dumps({
                "alignment_score": 0.85,
                "deviations": [
                    "Minor pacing differences in adaptation",
                    "Some supporting details condensed",
                ],
                "suggestions": ["Consider adding more visual cues"],
            })
        if "timeline" in sp:
            return self._demo_timeline()
        if "dialogue" in sp:
            return self._demo_dialogue()
        if "character" in sp:
            return self._demo_characters()
        if "narrative" in sp:
            return self._demo_narrative()
        if "world" in sp:
            return self._demo_world()
        if "critic" in sp:
            return json.dumps({"violations": [], "score": 0.92})
        if "repair" in sp:
            return "title: Repaired Screenplay\nlogline: Auto-fixed\nversion: 1"
        if "preprocessor" in sp or "preprocess" in sp:
            return self._demo_preprocess(user_prompt)
        if "screenplay planner" in sp or "batch" in sp:
            return self._demo_batch_plan()
        if "episode planner" in sp:
            return self._demo_episode_plan()
        if "scene planner" in sp or ("scene" in sp and "dialogue" not in sp):
            return self._demo_scene_plan()
        if "episode" in sp:
            return self._demo_episode_plan()
        return '{"result": "demo output"}'

    def _demo_characters(self):
        import json
        return json.dumps({"characters": [
            {"id": "char_001", "name": "Lin Ye", "role": "protagonist", "goal": "Save the city", "fear": "Losing control", "arc": "Self-sacrifice to redemption", "voice_style": "calm and resolute"},
            {"id": "char_002", "name": "Su Wan", "role": "supporting", "goal": "Protect Lin Ye", "fear": "Losing him", "arc": "From fear to courage", "voice_style": "emotional and caring"},
            {"id": "char_003", "name": "Dr. Chen", "role": "supporting", "goal": "Stabilize the rift", "fear": "Scientific failure", "arc": "Observer to participant", "voice_style": "analytical and precise"},
        ]}, ensure_ascii=False)

    def _demo_narrative(self):
        import json
        return json.dumps({"major_events": [
            {"chapter": 1, "description": "Lin Ye stands atop a skyscraper overlooking the twilight city, holding a blue-glowing chip.", "characters_involved": ["Lin Ye"]},
            {"chapter": 2, "description": "Alarm at the research institute - Dr. Chen detects the rift expanding.", "characters_involved": ["Lin Ye", "Dr. Chen"]},
            {"chapter": 3, "description": "Lin Ye decides to use his powers despite Su Wan plea.", "characters_involved": ["Lin Ye", "Su Wan"]},
            {"chapter": 4, "description": "The rift closes. Lin Ye collapses. A new light forms.", "characters_involved": ["Lin Ye", "Su Wan"]},
            {"chapter": 5, "description": "Three months later. The team enters the dimensional gate.", "characters_involved": ["Lin Ye", "Su Wan", "Dr. Chen"]},
        ], "subplots": [{"name": "The Sacrifice Bond", "description": "Lin Ye and Su Wan relationship tested", "related_characters": ["Lin Ye", "Su Wan"]}],
        "turning_points": [{"chapter": 3, "description": "Lin Ye chooses sacrifice", "impact": "Climax of character arc"}],
        "theme": "Sacrifice and redemption in the face of inevitable change"}, ensure_ascii=False)

    def _demo_world(self):
        import json
        return json.dumps({"world_rules": [
            {"domain": "magic", "description": "Dimensional energy can be harnessed at great cost"},
            {"domain": "technology", "description": "Advanced rift monitoring systems"},
        ], "geography": [{"name": "Twilight City", "description": "Neon metropolis rebuilt after crisis", "significance": "Main setting"}]})

    def _demo_timeline(self):
        import json
        return json.dumps({"events": [
            {"chapter": 1, "description": "Establishing the twilight city and rift"},
            {"chapter": 2, "description": "Rift instability detected at institute"},
            {"chapter": 3, "description": "Lin Ye defies Su Wan and uses his power"},
            {"chapter": 4, "description": "Rift closes, Lin Ye falls, new gate appears"},
            {"chapter": 5, "description": "Team enters the new world"},
        ]})

    def _demo_episode_plan(self):
        import json
        return json.dumps({"episodes": [
            {"id": "ep_001", "title": "The Twilight City", "summary": "Introduction to Lin Ye, the rift crisis, and the team"},
            {"id": "ep_002", "title": "The Choice", "summary": "The rift destabilizes. Lin Ye must choose."},
            {"id": "ep_003", "title": "New Horizon", "summary": "Aftermath and the gateway to a new dimension"},
        ]})

    def _demo_scene_plan(self):
        import json
        return json.dumps({"scenes": [
            {"scene_id": "sc_001", "location": "Rooftop", "time": "Night", "objective": "Establish setting", "conflict": "Man vs nature", "emotion": "Melancholic", "beats": [{"type": "action", "content": "Scene opens with a wide shot of the city below.", "emotion": None}]},
            {"scene_id": "sc_002", "location": "Research Institute", "time": "Night", "objective": "Reveal crisis", "conflict": "Time pressure", "emotion": "Urgent", "beats": [{"type": "action", "content": "Alarms blare as scientists scramble.", "emotion": None}]},
            {"scene_id": "sc_003", "location": "Rift Edge", "time": "Dawn", "objective": "Climax decision", "conflict": "Life vs duty", "emotion": "Tense", "beats": [{"type": "action", "content": "The protagonist stands at the edge of the rift.", "emotion": None}]},
        ]})

    def _demo_dialogue(self):
        import json
        return json.dumps({"scene_id": "sc_001", "location": "Rooftop", "time": "Night",
            "visual_focus": "Lin Ye at the edge, city lights below",
            "beats": [
                {"type": "action", "content": "Lin Ye steps onto the rooftop. Wind catches his coat.", "emotion": None},
                {"type": "dialogue", "character_id": "char_001", "content": "Three years since everything changed.", "emotion": "anticipation"},
                {"type": "action", "content": "He holds up the glowing chip.", "emotion": None},
                {"type": "dialogue", "character_id": "char_003", "content": "The readings are off the charts.", "emotion": "tension"},
                {"type": "dialogue", "character_id": "char_001", "content": "I have been ready for this.", "emotion": "resolve"},
            ], "transition": "fade", "duration_estimate": "120s"}, ensure_ascii=False)

    def _demo_preprocess(self, user_prompt):
        """Preprocess generic output (novel-agnostic demo)."""
        import json
        return json.dumps({
            "theme": "A story about conflict, growth and resolution",
            "logline": "In a world of challenges, a protagonist must overcome obstacles to achieve their goal.",
            "major_events": [
                {"ch": 1, "desc": "Inciting incident: the protagonist faces the first challenge", "chars": ["char_001"]},
                {"ch": 2, "desc": "Rising action: obstacles and conflicts intensify", "chars": ["char_001", "char_002"]},
                {"ch": 3, "desc": "Midpoint twist: new information changes the course", "chars": ["char_001", "char_003"]},
                {"ch": 4, "desc": "Climax building: protagonist confronts the core conflict", "chars": ["char_001", "char_002", "char_003"]},
                {"ch": 5, "desc": "Resolution: the conflict resolves, new equilibrium emerges", "chars": ["char_001", "char_002"]},
            ],
            "turning_points": [
                {"ch": 1, "desc": "First challenge appears", "impact": "Sets the story in motion"},
                {"ch": 3, "desc": "Key revelation changes protagonist perspective", "impact": "Deepens the conflict"},
                {"ch": 5, "desc": "Final confrontation and resolution", "impact": "Character arc completes"},
            ],
            "characters": [
                {"id": "char_001", "name": "Protagonist", "role": "protagonist",
                 "goal": "Overcome the central conflict", "fear": "Failure and loss",
                 "arc": "Ordinary person to hero", "voice_style": "Determined, evolving",
                 "traits": ["Courageous", "Resourceful", "Compassionate"]},
                {"id": "char_002", "name": "Ally", "role": "supporting",
                 "goal": "Help the protagonist succeed", "fear": "Losing the protagonist",
                 "arc": "Follower to partner", "voice_style": "Warm, supportive",
                 "traits": ["Loyal", "Wise", "Empathetic"]},
                {"id": "char_003", "name": "Antagonist", "role": "antagonist",
                 "goal": "Prevent the protagonist from succeeding", "fear": "Being defeated",
                 "arc": "Opponent to defeated", "voice_style": "Cold, commanding",
                 "traits": ["Powerful", "Cunning", "Ruthless"]},
            ],
            "locations": [
                {"name": "Main Location", "desc": "Primary setting where key events unfold", "scenes": ["Opening", "Climax"]},
                {"name": "Secondary Location", "desc": "Secondary setting for supporting scenes", "scenes": ["Development", "Turning point"]},
            ],
        }, ensure_ascii=False)
    def _demo_batch_plan(self):
        """Batch plan generic output (novel-agnostic demo)."""
        import json
        return json.dumps({
            "episodes": [
                {
                    "id": "ep_001", "title": "The Beginning",
                    "summary": "The protagonist faces the initial challenge and meets key characters.",
                    "theme": "Introduction and inciting incident",
                    "pacing": "Slow build to hook",
                    "scenes": [
                        {
                            "scene_id": "sc_001", "location": "Main Location - Interior", "time": "Day",
                            "objective": "Establish the protagonist world and the normal state", "conflict": "Hint of coming disruption", "emotion": "Calm before storm",
                            "characters_present": ["char_001"],
                            "beats": [
                                {"type": "action", "character_id": None, "content": "The protagonist arrives at the main location. The atmosphere is tense.", "emotion": None},
                                {"type": "dialogue", "character_id": "char_001", "content": "This is where it all begins.", "emotion": "resolve"},
                                {"type": "action", "character_id": None, "content": "A sudden event disrupts the calm.", "emotion": None},
                                {"type": "dialogue", "character_id": "char_001", "content": "What just happened?", "emotion": "surprise"},
                            ],
                            "transition": "fade", "duration_estimate": "3min",
                        },
                        {
                            "scene_id": "sc_002", "location": "Main Location - Exterior", "time": "Night",
                            "objective": "Protagonist encounters the first obstacle", "conflict": "External force opposes the protagonist", "emotion": "Urgent",
                            "characters_present": ["char_001", "char_002"],
                            "beats": [
                                {"type": "action", "character_id": None, "content": "The protagonist moves through the night, searching for answers.", "emotion": None},
                                {"type": "dialogue", "character_id": "char_002", "content": "You should not be here. It is dangerous.", "emotion": "fear"},
                                {"type": "action", "character_id": None, "content": "A figure appears in the distance.", "emotion": None},
                            ],
                            "transition": "dissolve", "duration_estimate": "2min",
                        },
                        {
                            "scene_id": "sc_003", "location": "Secondary Location", "time": "Morning",
                            "objective": "Protagonist learns crucial information", "conflict": "Truth is more complex than expected", "emotion": "Revelation",
                            "characters_present": ["char_001", "char_002"],
                            "beats": [
                                {"type": "action", "character_id": None, "content": "Inside the secondary location, a hidden terminal flickers.", "emotion": None},
                                {"type": "dialogue", "character_id": "char_002", "content": "There is something you need to see.", "emotion": "calm"},
                                {"type": "dialogue", "character_id": "char_001", "content": "This changes everything.", "emotion": "surprise"},
                            ],
                            "transition": "cut", "duration_estimate": "4min",
                        },
                    ],
                },
                {
                    "id": "ep_002", "title": "The Conflict",
                    "summary": "Tensions rise as the antagonist makes a move. The protagonist must adapt.",
                    "theme": "Rising stakes and confrontation",
                    "pacing": "Building tension",
                    "scenes": [
                        {
                            "scene_id": "sc_004", "location": "Antagonist Stronghold", "time": "Night",
                            "objective": "Antagonist reveals their plan", "conflict": "Protagonist is outmatched", "emotion": "Tense",
                            "characters_present": ["char_003"],
                            "beats": [
                                {"type": "action", "character_id": None, "content": "The antagonist surveys their domain. Plans are already in motion.", "emotion": None},
                                {"type": "dialogue", "character_id": "char_003", "content": "Nothing will stand in my way.", "emotion": "calm"},
                                {"type": "action", "character_id": None, "content": "Orders are given. The trap is set.", "emotion": None},
                            ],
                            "transition": "dissolve", "duration_estimate": "4min",
                        },
                        {
                            "scene_id": "sc_005", "location": "Main Location", "time": "Day",
                            "objective": "Protagonist confronts the danger directly", "conflict": "Direct confrontation with antagonist forces", "emotion": "High tension",
                            "characters_present": ["char_001", "char_003"],
                            "beats": [
                                {"type": "action", "character_id": None, "content": "The protagonist arrives, ready for confrontation.", "emotion": None},
                                {"type": "dialogue", "character_id": "char_003", "content": "You should have stayed away.", "emotion": "anger"},
                                {"type": "dialogue", "character_id": "char_001", "content": "I will not back down.", "emotion": "resolve"},
                            ],
                            "transition": "cut", "duration_estimate": "3min",
                        },
                    ],
                },
                {
                    "id": "ep_003", "title": "The Resolution",
                    "summary": "The final confrontation. The protagonist makes the ultimate choice.",
                    "theme": "Climax and resolution",
                    "pacing": "Fast-paced climax",
                    "scenes": [
                        {
                            "scene_id": "sc_006", "location": "Final Location", "time": "Twilight",
                            "objective": "The ultimate confrontation and resolution", "conflict": "Everything is at stake", "emotion": "Emotional climax",
                            "characters_present": ["char_001", "char_002", "char_003"],
                            "beats": [
                                {"type": "action", "character_id": None, "content": "The protagonist stands at the final location. The endgame begins.", "emotion": None},
                                {"type": "dialogue", "character_id": "char_001", "content": "This ends now.", "emotion": "resolve"},
                                {"type": "action", "character_id": None, "content": "The final confrontation unfolds. Everything the protagonist has learned comes together.", "emotion": None},
                                {"type": "dialogue", "character_id": "char_002", "content": "You did it. It is over.", "emotion": "calm"},
                            ],
                            "transition": "fade", "duration_estimate": "3min",
                        },
                    ],
                },
            ],
        }, ensure_ascii=False)
# Global singleton
llm_client = LLMClient()

