from __future__ import annotations

import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class BeatType(str, Enum):
    DIALOGUE = "dialogue"
    ACTION = "action"
    SILENCE = "silence"
    REACTION = "reaction"


class Transition(str, Enum):
    CUT = "cut"
    FADE = "fade"
    DISSOLVE = "dissolve"
    WIPE = "wipe"


class CharacterRole(str, Enum):
    PROTAGONIST = "protagonist"
    ANTAGONIST = "antagonist"
    SUPPORTING = "supporting"


class Character(BaseModel):
    id: str = Field(pattern=r"^char_\d+$")
    name: str
    role: CharacterRole
    goal: str
    fear: str = ""
    arc: str
    voice_style: str = ""


class Beat(BaseModel):
    type: BeatType
    character_id: str | None = None
    content: str
    emotion: str | None = None


class Scene(BaseModel):
    scene_id: str = Field(pattern=r"^sc_\d+$")
    location: str
    time: str
    visual_focus: str | None = None
    sound_effect: str | None = None
    voice_over: str | None = None
    beats: list[Beat] = Field(default_factory=list)
    transition: Transition = Transition.CUT
    duration_estimate: str = "60s"


class Episode(BaseModel):
    id: str = Field(pattern=r"^ep_\d+$")
    title: str
    summary: str
    scenes: list[Scene] = Field(default_factory=list)


class Screenplay(BaseModel):
    title: str
    logline: str
    genre: str
    theme: str
    characters: list[Character] = Field(default_factory=list)
    episodes: list[Episode] = Field(default_factory=list)


class NarrativeOutput(BaseModel):
    title: str
    logline: str
    genre: str
    theme: str
    core_conflict: str
    tone: str = ""
    target_audience: str = ""
    style_notes: str = ""


class CharacterOutput(BaseModel):
    characters: list[Character] = Field(default_factory=list)


class WorldOutput(BaseModel):
    locations: list[dict[str, Any]] = Field(default_factory=list)
    world_rules: list[dict[str, Any]] = Field(default_factory=list)
    atmosphere: str = ""


class TimelineOutput(BaseModel):
    events: list[dict[str, Any]] = Field(default_factory=list)
    timeline_type: str = "linear"
    major_turning_points: list[str] = Field(default_factory=list)


class EpisodePlannerOutput(BaseModel):
    episodes: list[dict[str, Any]] = Field(default_factory=list)
    season_arc: str = ""


class ScenePlannerOutput(BaseModel):
    episode_id: str = ""
    scenes: list[dict[str, Any]] = Field(default_factory=list)


class DialogueOutput(BaseModel):
    beats: list[dict[str, Any]] = Field(default_factory=list)


class CriticOutput(BaseModel):
    score: float = Field(default=0.0, ge=0.0, le=10.0)
    issues: list[dict[str, Any]] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    overall_assessment: str = ""


class RepairOutput(BaseModel):
    repaired_yaml: str = ""
    changes_made: list[dict[str, Any]] = Field(default_factory=list)
    validation_passed: bool = False


class ConsistencyOutput(BaseModel):
    consistent: bool = True
    issues: list[dict[str, Any]] = Field(default_factory=list)
    resolved: bool = False


class ConvertRequest(BaseModel):
    novel_text: str
    mode: str = "auto"
    pipeline: str = "full"


class ConvertResponse(BaseModel):
    task_id: str
    status: str
    message: str = ""
    yaml_content: str = ""
    screenplay: Screenplay | None = None


class TaskStatus(BaseModel):
    task_id: str
    status: str
    progress: float = 0.0
    current_stage: str = ""
    output: str = ""
    error: str = ""


class UploadResponse(BaseModel):
    task_id: str
    filename: str
    char_count: int
    language: str
    chapter_count: int = 0


class ImportEditsResponse(BaseModel):
    task_id: str
    status: str
    validated: bool = False
    repaired_yaml: str = ""
    changes: list[str] = Field(default_factory=list)


class AlignmentResponse(BaseModel):
    task_id: str
    original_text_alignment: list[dict[str, Any]] = Field(default_factory=list)
    scene_to_source: list[dict[str, Any]] = Field(default_factory=list)


class ValidateResponse(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class UsageStats(BaseModel):
    total_llm_calls: int = 0
    total_tokens: int = 0
    total_cost_estimate: float = 0.0


class DetectLanguageResponse(BaseModel):
    language: str
    confidence: float = 1.0


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "2.0.0"


class NovelUploadRequest(BaseModel):
    content: str
    filename: str = ""


class ValidationReport(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
