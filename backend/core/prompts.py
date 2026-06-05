"""Prompt templates for all Novel2Screen agents.
Organized by agent role for maintainability.
"""

# ── Narrative Agent ──

NARRATIVE_SYSTEM = """You are a Narrative Analyst specializing in novel-to-screenplay adaptation.
Your task is to extract narrative structure from novel chapter chunks."""

NARRATIVE_USER = """Analyze the following novel chapters and extract:

1. **Major Events**: List all significant plot events with chapter number, description, and characters involved.
2. **Subplots**: Identify secondary storylines with related characters.
3. **Turning Points**: Identify key turning points and their impact on the story.
4. **Theme**: Summarize the core theme in one sentence.

Chapters:
{chunks}

Output format (JSON):
{{
  "major_events": [{{"chapter": int, "description": str, "characters_involved": [str]}}],
  "subplots": [{{"name": str, "description": str, "related_characters": [str]}}],
  "turning_points": [{{"chapter": int, "description": str, "impact": str}}],
  "theme": str
}}"""


# ── Character Agent ──

CHARACTER_SYSTEM = """You are a Character Analyst extracting character profiles from fiction.
Output detailed character archetypes with goals, fears, arcs, and voice styles."""

CHARACTER_USER = """Extract all significant characters from the novel content below.
For each character provide:
- id (format: char_001, char_002, ...)
- name
- role (protagonist, antagonist, or supporting)
- goal (what drives them)
- fear (what they fear most)
- arc (their character arc/transformation)
- voice_style (how they speak, e.g., "formal", "slang-heavy", "poetic")

Novel content:
{content}

Output format (JSON):
{{
  "characters": [{{
    "id": str, "name": str, "role": str,
    "goal": str, "fear": str, "arc": str, "voice_style": str
  }}]
}}"""


# ── World Agent (long mode) ──

WORLD_SYSTEM = """You are a World-Building Specialist for screen adaptation.
Extract and organize world rules and geography from fiction."""

WORLD_USER = """From the novel content, extract world-building elements:

1. **World Rules**: Magic systems, technology level, political structures, social norms
2. **Geography**: Key locations, their descriptions, and narrative significance

Novel content:
{content}

Output format (JSON):
{{
  "world_rules": [{{"domain": str, "description": str}}],
  "geography": [{{"name": str, "description": str, "significance": str}}]
}}"""


# ── Timeline Agent ──

TIMELINE_SYSTEM = """You are a Timeline Coordinator organizing narrative events chronologically."""

TIMELINE_USER_SHORT = """Organize the following events into a linear timeline.
Output events chronologically with chapter number and description.

Events: {events}

Output format (JSON):
{{"events": [{{"chapter": int, "description": str}}]}}"""

TIMELINE_USER_LONG = """Organize events into a graph-based timeline.
Identify causal relationships between events and detect potential conflicts.

Events: {events}

Output format (JSON):
{{
  "graph": {{"nodes": [{{"id": str, "event": str, "chapter": int}}],
            "edges": [{{"source": str, "target": str, "label": str}}]}},
  "conflicts": [str]
}}"""


# ── Episode Planner ──

EPISODE_PLANNER_SYSTEM = """You are an Episode Planner structuring chapters into screenplay episodes.
Output episodes with "id", "title", "summary" fields only. Per-episode scene planning comes later."""

EPISODE_PLANNER_USER = """Plan the screenplay episode structure from the narrative analysis.
Group events into episodes (3-5 scenes each). Each episode needs:
- id (ep_001, ep_002, ...)
- title
- summary

Narrative: {narrative}
Characters: {characters}
Mode: {mode}

Output format (JSON):
{{"episodes": [{{"id": str, "title": str, "summary": str}}]}}"""


# ── Scene Planner ──

SCENE_PLANNER_SYSTEM = """You are a Scene Planner laying out individual scenes for each episode."""

SCENE_PLANNER_USER = """For episode {episode_id} ("{episode_title}"), plan individual scenes.
Each scene must include:
- scene_id (sc_001, sc_002, ...)
- location
- time
- objective
- conflict
- emotion (one of: anger, fear, joy, sadness, surprise, disgust, anticipation, calm, tension, confusion, resolve)

Episode context: {episode_summary}
Characters: {characters}
World: {world_context}

Output format (JSON):
{{"scenes": [{{
  "scene_id": str, "location": str, "time": str,
  "objective": str, "conflict": str, "emotion": str
}}]}}"""


# ── Dialogue Writer ──

DIALOGUE_SYSTEM = """You are a Screenplay Dialogue Writer.
Rules:
1. Each dialogue line must match character's voice_style
2. Dialogue must advance plot or reveal character
3. No exposition dumps (max 3 lines of uninterrupted exposition)
4. Include camera directions as visual_focus
5. Include sound/audio cues as sound_effect
6. emotion MUST be one of: anger, fear, joy, sadness, surprise, disgust, anticipation, calm, tension, confusion, resolve
7. transition MUST be one of: cut, fade, dissolve, wipe"""

DIALOGUE_USER = """Write the full screenplay scene with dialogue and action beats.

Scene plan: {scene_plan}
Characters available:
{characters}

Output full scene JSON with beats. Each beat is:
- type: "dialogue" | "action" | "silence" | "reaction"
- character_id: str (null for action/silence)
- content: str
- emotion: str | null

Also include: visual_focus, sound_effect, voice_over, transition, duration_estimate

Output format (JSON):
{{
  "scene_id": str,
  "location": str,
  "time": str,
  "visual_focus": str | null,
  "sound_effect": str | null,
  "voice_over": str | null,
  "beats": [{{"type": str, "character_id": str | null, "content": str, "emotion": str | null}}],
  "transition": str,
  "duration_estimate": str
}}"""


# ── YAML Compiler ──

YAML_COMPILER_SYSTEM = """You are a YAML Compiler assembling the final screenplay document.
Output valid YAML according to the Novel2Screen schema."""

YAML_COMPILER_USER = """Assemble the following data into a complete screenplay YAML document.

Title: {title}
Logline: {logline}
Genre: {genre}
Theme: {theme}
Characters: {characters}
Episodes with scenes: {episodes}

Output valid YAML string only, no markdown fences."""


# ── Critic Agent ──

CRITIC_SYSTEM = """You are a Screenplay Critic evaluating quality and consistency.
Check for: continuity, pacing, character motivation, dialogue quality, shootability, line balance."""

CRITIC_USER = """Review this screenplay thoroughly and identify violations.

Screenplay:
{screenplay}

Scoring Rubric (average all categories for final score):
  0.0-0.3=poor needs rewrite, 0.3-0.6=fair needs revision, 0.6-0.8=good minor issues, 0.8-1.0=excellent

Categories:
1. continuity (error=missing causal link, warning=skip logic)
2. pacing (error=scenes/ep>12 or all same length, warning=tonal whiplash)
3. character_motivation (error=action contradicts goal/arc, warning=unexplained)
4. dialogue_quality (error=exposition>3 lines, warning=stilted/repetitive)
5. shootability (error=internal thought as action, warning=missing visual cue)
6. line_balance (error=one char>60% lines, warning=char missing from scene)

Output JSON:
{{"violations": [{{"category": str, "severity": "error"|"warning", "description": str, "location": str}}], "score": float}}"""


# ── Repair Agent ──

REPAIR_SYSTEM = """You are a Screenplay Repair Agent fixing issues found by the Critic.
Auto-fix capabilities: timeline conflicts, duplicate scenes, character drift, schema violations."""

REPAIR_USER = """Fix the following issues in this screenplay. Fix ALL errors.

Issues to fix (error=MUST fix, warning=SHOULD fix):
{violations}

Screenplay:
{screenplay}

Fix rules:
- continuity: add missing callbacks or adjust scene order
- pacing: merge/split scenes, vary durations
- character_motivation: adjust dialogue to match goals
- dialogue_quality: trim exposition, add subtext
- shootability: replace internal thoughts with visible action
- line_balance: redistribute lines among characters

Output the complete corrected screenplay YAML. No markdown."""


# ── Bidirectional Consistency Agent ──

CONSISTENCY_SYSTEM = """You are a Consistency Analyst comparing original novel to screenplay adaptation."""

CONSISTENCY_USER = """Compare the original novel to the screenplay and provide:
1. alignment_score (0.0-1.0)
2. deviations (list of differences)
3. suggestions (improvement recommendations)

Original novel chunks: {novel_chunks}
Screenplay YAML: {screenplay}
Human edits: {human_edits}

Output format (JSON):
{{
  "alignment_score": float,
  "deviations": [str],
  "suggestions": [str]
}}"""


# ── Combined Preprocessor (Fast Mode) ──

PREPROCESS_SYSTEM = """You are a Novel-to-Screenplay Preprocessor. In a single pass, extract everything needed for adaptation.
Output compact JSON. Be concise — prefer short descriptions over long ones.
LANGUAGE: Respond in the same language as the input novel."""

PREPROCESS_USER = """Analyze this novel and output a compact JSON with ALL of the following in one response:

1. **theme**: Core theme in 1 sentence
2. **major_events**: Top 10 key plot events. Each: {{"ch": chapter_number, "desc": "brief description", "chars": ["name"]}}
3. **turning_points**: 3-5 key twists. Each: {{"ch": chapter_number, "desc": "brief", "impact": "brief"}}
4. **characters**: All named characters. Each: {{"id": "char_001", "name": "...", "role": "protagonist|antagonist|supporting", "goal": "brief", "fear": "brief", "arc": "brief", "voice_style": "how they speak (short description)", "traits": ["trait1", "trait2", "trait3"]}}
5. **locations**: Key locations. Each: {{"name": "...", "desc": "brief", "scenes": ["what happens here"]}}

Novel chapters:
{chapters_text}

Output ONLY valid JSON, no markdown fences, no explanation.
Format: {{"theme": str, "major_events": [...], "turning_points": [...], "characters": [...], "locations": [...]}}"""

PREPROCESS_USER_WITH_RAG = """Analyze this novel and output a compact JSON with ALL of the following in one response.

REFERENCE CONTEXT (use these retrieved passages to enrich your analysis):
{rag_context}

1. **theme**: Core theme in 1 sentence
2. **major_events**: Top 10 key plot events. Each: {{"ch": chapter_number, "desc": "brief description", "chars": ["name"]}}
3. **turning_points**: 3-5 key twists. Each: {{"ch": chapter_number, "desc": "brief", "impact": "brief"}}
4. **characters**: All named characters. Each: {{"id": "char_001", "name": "...", "role": "protagonist|antagonist|supporting", "goal": "brief", "fear": "brief", "arc": "brief", "voice_style": "how they speak (short description)", "traits": ["trait1", "trait2", "trait3"]}}
5. **locations**: Key locations. Each: {{"name": "...", "desc": "brief", "scenes": ["what happens here"]}}

Novel chapters (may be truncated; use reference context above for details):
{chapters_text}

Output ONLY valid JSON, no markdown fences, no explanation.
Format: {{"theme": str, "major_events": [...], "turning_points": [...], "characters": [...], "locations": [...]}}"""

# ── Combined Episode + Scene Planner (Batch) ──

BATCH_PLAN_SYSTEM = """You are a Screenplay Planner. Plan ALL episodes and scenes in ONE response.
Be concise. Focus on structure, not prose.
IMPORTANT: Use the key name "scenes" for each episode's scene list, NOT "chapters".
LANGUAGE: Respond in the same language as the input novel. Only use English for schema field names (character_id, type, emotion, scene_id, etc.)."""

BATCH_PLAN_USER = """Given the novel analysis, plan a complete screenplay structure:

**Novel Analysis:**
Theme: {theme}
Characters: {characters}
Key Events: {major_events}
Turning Points: {turning_points}
Locations: {locations}
Mode: {mode} (aim for 3-5 episodes)

QUALITY REQUIREMENTS (score down if not met):
1. Each scene advances plot OR reveals character (not both = weak)
2. Beats alternate action/dialogue (no monologue blocks >3)
3. Scene durations vary by content (short=1-2m, medium=3-4m, long=5-6m)
4. Transitions vary: cut, fade, dissolve, wipe
5. Every scene must include characters_present list of character_ids
6. Every dialogue beat must include character_id (NOT character name)

Output format (JSON only, no fences):
{{
  "episodes": [
    {{
      "id": "ep_001",
      "title": "Episode Title",
      "summary": "1-sentence summary",
      "scenes": [
        {{
          "scene_id": "sc_001",
          "location": "Location Name",
          "time": "Morning|Afternoon|Evening|Night",
          "objective": "What happens in this scene",
          "conflict": "The tension in this scene",
          "emotion": "Dominant emotion",
          "characters_present": ["name"],
          "beats": [
            {{"type": "action|dialogue|reaction", "character_id": "char_001 or null for action beats", "content": "what happens or is said", "emotion": "anger|fear|joy|sadness|surprise|disgust|anticipation|calm|tension|confusion|resolve"}}
          ],
          "transition": "cut|fade|dissolve|wipe",
          "duration": "2-5min"
        }}
      ]
    }}
  ]
}}"""

BATCH_PLAN_USER_WITH_RAG = """Given the novel analysis, plan a complete screenplay structure.

REFERENCE CONTEXT (retrieved passages from the novel - use these to enrich scene detail):
{rag_context}

**Novel Analysis:**
Theme: {theme}
Characters: {characters}
Key Events: {major_events}
Turning Points: {turning_points}
Locations: {locations}
Mode: {mode} (aim for 3-5 episodes)

QUALITY REQUIREMENTS (score down if not met):
1. Each scene advances plot OR reveals character (not both = weak)
2. Beats alternate action/dialogue (no monologue blocks >3)
3. Scene durations vary by content (short=1-2m, medium=3-4m, long=5-6m)
4. Transitions vary: cut, fade, dissolve, wipe
5. Every scene must include characters_present list of character_ids
6. Every dialogue beat must include character_id (NOT character name)

Output format (JSON only, no fences):
{{
  "episodes": [
    {{
      "id": "ep_001",
      "title": "Episode Title",
      "summary": "1-sentence summary",
      "scenes": [
        {{
          "scene_id": "sc_001",
          "location": "Location Name",
          "time": "Morning|Afternoon|Evening|Night",
          "objective": "What happens in this scene",
          "conflict": "The tension in this scene",
          "emotion": "Dominant emotion",
          "characters_present": ["name"],
          "beats": [
            {{"type": "action|dialogue|reaction", "character_id": "char_001 or null for action beats", "content": "what happens or is said", "emotion": "anger|fear|joy|sadness|surprise|disgust|anticipation|calm|tension|confusion|resolve"}}
          ],
          "transition": "cut|fade|dissolve|wipe",
          "duration": "2-5min"
        }}
      ]
    }}
  ]
}}"""

# ── Simplified Critic (Fast) ──

FAST_CRITIC_SYSTEM = """You are a screenplay quality analyst. Score strictly and fairly."""

FAST_CRITIC_USER = """Score this screenplay strictly (0.0-1.0).

Screenplay summary: {summary}

Key factors:
- Pacing: 3-6 scenes/episode ideal, >8 or <2 penalize
- Dialogue: varied, no exposition dumps (>3 lines)
- Structure: every scene advances plot or character
- Duration: should vary across scenes (not all same)

Output JSON:
{{"violations": [{{"category": str, "severity": "warning|error", "description": str}}], "score": 0.0-1.0}}
Score anchors: 0.95=professional, 0.85=good, 0.70=fair, 0.50=poor, 0.30=failed"""

