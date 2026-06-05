"""
Pydantic models for Novel2Screen data schemas.
Matches the YAML schema spec from the design document.
"""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


# ── Beat Types ──

class BeatType(str, Enum):
    dialogue = "dialogue"
    action = "action"
    silence = "silence"
    reaction = "reaction"


class Transition(str, Enum):
    cut = "cut"
    fade = "fade"
    dissolve = "dissolve"
    wipe = "wipe"


class Emotion(str, Enum):
    anger = "anger"
    fear = "fear"
    joy = "joy"
    sadness = "sadness"
    surprise = "surprise"
    disgust = "disgust"
    anticipation = "anticipation"
    calm = "calm"
    tension = "tension"
    confusion = "confusion"
    resolve = "resolve"


# ── Character ──

class CharacterRole(str, Enum):
    protagonist = "protagonist"
    antagonist = "antagonist"
    supporting = "supporting"


class Character(BaseModel):
    id: str = Field(pattern=r"^char_\d+$")
    name: str
    role: CharacterRole
    goal: str
    fear: str = ""
    arc: str
    voice_style: str = ""
    traits: list[str] = Field(default_factory=list)


# ── Beat ──

class Beat(BaseModel):
    type: BeatType
    character_id: Optional[str] = None
    content: str
    emotion: Optional[str] = None


# ── Scene ──

class Scene(BaseModel):
    scene_id: str = Field(pattern=r"^sc_\d+$")
    location: str
    time: str
    visual_focus: Optional[str] = None
    sound_effect: Optional[str] = None
    voice_over: Optional[str] = None
    beats: list[Beat] = Field(default_factory=list, min_length=1)
    transition: str = "cut"
    duration_estimate: str = "120s"


# ── Episode ──

class Episode(BaseModel):
    id: str = Field(pattern=r"^ep_\d+$")
    title: str
    summary: str
    theme: str = ""
    pacing: str = ""
    scenes: list[Scene] = Field(default_factory=list)


# ── Root Screenplay ──

class Screenplay(BaseModel):
    schema_version: str = "1.0"
    title: str
    logline: str
    genre: str
    theme: str
    characters: list[Character] = Field(default_factory=list, min_length=1)
    episodes: list[Episode] = Field(default_factory=list, min_length=1)


# ── Narrative Agent Output ──

class MajorEvent(BaseModel):
    chapter: int
    description: str
    characters_involved: list[str] = Field(default_factory=list)


class Subplot(BaseModel):
    name: str
    description: str
    related_characters: list[str] = Field(default_factory=list)


class TurningPoint(BaseModel):
    chapter: int
    description: str
    impact: str = ""


class NarrativeOutput(BaseModel):
    major_events: list[MajorEvent]
    subplots: list[Subplot]
    turning_points: list[TurningPoint]
    theme: str


# ── Character Agent Output ──

class CharacterOutput(BaseModel):
    characters: list[Character]


# ── World Agent Output ──

class WorldRule(BaseModel):
    domain: str  # magic, technology, politics, etc.
    description: str


class Location(BaseModel):
    name: str
    description: str
    significance: str = ""


class WorldOutput(BaseModel):
    world_rules: list[WorldRule] = Field(default_factory=list)
    geography: list[Location] = Field(default_factory=list)


# ── Timeline Agent Output ──

class TimelineEvent(BaseModel):
    chapter: int
    description: str


class TimelineNode(BaseModel):
    id: str
    event: str
    chapter: int


class TimelineEdge(BaseModel):
    source: str
    target: str
    label: str = ""


class TimelineOutput(BaseModel):
    events: list[TimelineEvent] = Field(default_factory=list)
    graph: Optional[dict] = None  # nodes + edges for long mode
    conflicts: list[str] = Field(default_factory=list)


# ── Episode Planner Output ──

class EpisodePlan(BaseModel):
    episodes: list[Episode]


# ── Scene Planner Output ──

class ScenePlan(BaseModel):
    scenes: list[Scene]


# ── Dialogue Output ──

class DialogueOutput(BaseModel):
    scenes: list[Scene]


# ── Critic Violation ──

class Violation(BaseModel):
    category: str  # continuity, pacing, character_motivation, dialogue, shootability, line_balance
    severity: str  # error, warning
    description: str
    location: str = ""


class CriticOutput(BaseModel):
    violations: list[Violation] = Field(default_factory=list)
    score: float = 1.0


# ── Repair Output ──

class RepairOutput(BaseModel):
    screenplay: Screenplay
    changes_made: list[str] = Field(default_factory=list)


# ── Consistency Agent Output ──

class ConsistencyOutput(BaseModel):
    alignment_score: float = Field(ge=0.0, le=1.0)
    deviations: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
