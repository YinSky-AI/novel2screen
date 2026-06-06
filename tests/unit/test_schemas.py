from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.schemas.models import (
    AlignmentResponse,
    Beat,
    BeatType,
    Character,
    CharacterOutput,
    CharacterRole,
    ConsistencyOutput,
    ConvertRequest,
    ConvertResponse,
    CriticOutput,
    DetectLanguageResponse,
    DialogueOutput,
    Episode,
    EpisodePlannerOutput,
    HealthResponse,
    ImportEditsResponse,
    NarrativeOutput,
    RepairOutput,
    Scene,
    ScenePlannerOutput,
    Screenplay,
    TaskStatus,
    TimelineOutput,
    Transition,
    UploadResponse,
    UsageStats,
    ValidateResponse,
    WorldOutput,
)


# ---------------------------------------------------------------------------
# Minimal screenplay (valid)
# ---------------------------------------------------------------------------

class TestMinimalScreenplay:
    def test_minimal_valid(self) -> None:
        sp = Screenplay(
            title="Min",
            logline="A minimal test.",
            genre="Test",
            theme="Minimal",
        )
        assert sp.title == "Min"
        assert sp.characters == []
        assert sp.episodes == []

    def test_full_screenplay_valid(self) -> None:
        sp = Screenplay(
            title="Full",
            logline="A full test.",
            genre="Drama",
            theme="Full test",
            characters=[
                Character(
                    id="char_001",
                    name="Hero",
                    role=CharacterRole.PROTAGONIST,
                    goal="Win",
                    arc="Growth",
                ),
            ],
            episodes=[
                Episode(
                    id="ep_001",
                    title="First",
                    summary="Episode one",
                    scenes=[
                        Scene(
                            scene_id="sc_001",
                            location="Room",
                            time="Day",
                            beats=[
                                Beat(type=BeatType.DIALOGUE, character_id="char_001", content="Let's go!"),
                            ],
                        ),
                    ],
                ),
            ],
        )
        assert sp.title == "Full"
        assert len(sp.characters) == 1
        assert len(sp.episodes) == 1


# ---------------------------------------------------------------------------
# Missing required fields
# ---------------------------------------------------------------------------

class TestMissingRequiredFields:
    def test_screenplay_missing_title(self) -> None:
        with pytest.raises(ValidationError):
            Screenplay(logline="No title", genre="X", theme="X")

    def test_episode_missing_id(self) -> None:
        with pytest.raises(ValidationError):
            Episode(title="No ID", summary="Missing id")

    def test_scene_missing_id(self) -> None:
        with pytest.raises(ValidationError):
            Scene(location="Room", time="Now")

    def test_beat_missing_type(self) -> None:
        with pytest.raises(ValidationError):
            Beat(content="No type")

    def test_character_missing_name(self) -> None:
        with pytest.raises(ValidationError):
            Character(id="char_001", role=CharacterRole.SUPPORTING, goal="G", arc="A")


# ---------------------------------------------------------------------------
# Invalid type IDs
# ---------------------------------------------------------------------------

class TestInvalidTypeIDs:
    def test_invalid_episode_id_format(self) -> None:
        with pytest.raises(ValidationError):
            Episode(id="bad", title="X", summary="X")

    def test_invalid_scene_id_format(self) -> None:
        with pytest.raises(ValidationError):
            Scene(scene_id="scene-1", location="X", time="X")

    def test_invalid_beat_type(self) -> None:
        with pytest.raises(ValidationError):
            Beat(type="singing", content="Not a valid type")


# ---------------------------------------------------------------------------
# Invalid transition
# ---------------------------------------------------------------------------

class TestInvalidTransition:
    def test_invalid_transition(self) -> None:
        with pytest.raises(ValidationError):
            Scene(
                scene_id="sc_001",
                location="Room",
                time="Now",
                transition="jump",
            )

    def test_valid_transitions(self) -> None:
        for t in ("cut", "fade", "dissolve", "wipe"):
            s = Scene(scene_id="sc_001", location="Room", time="Now", transition=Transition(t))
            assert s.transition == Transition(t)


# ---------------------------------------------------------------------------
# Invalid character role
# ---------------------------------------------------------------------------

class TestInvalidCharacterRole:
    def test_invalid_role(self) -> None:
        with pytest.raises(ValidationError):
            Character(id="char_001", name="Bad", role="extra", goal="G", arc="A")

    def test_valid_roles(self) -> None:
        for role in ("protagonist", "antagonist", "supporting"):
            c = Character(
                id="char_001",
                name="Test",
                role=CharacterRole(role),
                goal="Goal",
                arc="Arc",
            )
            assert c.role == CharacterRole(role)


# ---------------------------------------------------------------------------
# Max scenes constraint
# ---------------------------------------------------------------------------

class TestMaxScenesConstraint:
    def test_many_scenes(self) -> None:
        scenes = [
            Scene(
                scene_id=f"sc_{i:03d}",
                location=f"Loc{i}",
                time="Day",
                beats=[Beat(type=BeatType.ACTION, content="x")],
            )
            for i in range(1, 51)
        ]
        ep = Episode(id="ep_001", title="Many", summary="50 scenes", scenes=scenes)
        assert len(ep.scenes) == 50


# ---------------------------------------------------------------------------
# Agent output model tests
# ---------------------------------------------------------------------------

class TestAgentOutputModels:
    def test_narrative_output_valid(self) -> None:
        o = NarrativeOutput(
            title="T",
            logline="L",
            genre="G",
            theme="Th",
            core_conflict="CC",
            tone="dark",
            target_audience="adults",
            style_notes="cinematic",
        )
        assert o.title == "T"

    def test_narrative_output_minimal(self) -> None:
        o = NarrativeOutput(
            title="T",
            logline="L",
            genre="G",
            theme="Th",
            core_conflict="C",
        )
        assert o.tone == ""

    def test_character_output(self) -> None:
        o = CharacterOutput(characters=[])
        assert o.characters == []

    def test_world_output(self) -> None:
        o = WorldOutput(locations=[], world_rules=[], atmosphere="dark")
        assert o.atmosphere == "dark"

    def test_timeline_output(self) -> None:
        o = TimelineOutput(
            events=[{"order": 1, "description": "Start"}],
            timeline_type="linear",
            major_turning_points=["The reveal"],
        )
        assert o.events[0]["description"] == "Start"

    def test_episode_planner_output(self) -> None:
        o = EpisodePlannerOutput(episodes=[], season_arc="")
        assert o.episodes == []

    def test_scene_planner_output(self) -> None:
        o = ScenePlannerOutput(episode_id="ep_001", scenes=[])
        assert o.episode_id == "ep_001"

    def test_dialogue_output(self) -> None:
        o = DialogueOutput(beats=[{"type": "dialogue", "content": "Hi"}])
        assert len(o.beats) == 1

    def test_critic_output_score_range(self) -> None:
        o = CriticOutput(score=7.5, issues=[], suggestions=[], overall_assessment="Good")
        assert 0 <= o.score <= 10

    def test_critic_output_score_out_of_range(self) -> None:
        with pytest.raises(ValidationError):
            CriticOutput(score=15.0, issues=[], suggestions=[], overall_assessment="Bad")

    def test_repair_output(self) -> None:
        o = RepairOutput(
            repaired_yaml="title: X",
            changes_made=[{"field": "title", "before": "?", "after": "X"}],
            validation_passed=True,
        )
        assert o.repaired_yaml == "title: X"
        assert o.validation_passed

    def test_consistency_output(self) -> None:
        o = ConsistencyOutput(consistent=True, issues=[], resolved=True)
        assert o.consistent
        assert o.resolved


# ---------------------------------------------------------------------------
# API request/response models
# ---------------------------------------------------------------------------

class TestAPIRequestResponse:
    def test_convert_request(self) -> None:
        r = ConvertRequest(novel_text="Once upon a time...")
        assert r.mode == "auto"
        assert r.pipeline == "full"

    def test_convert_response(self) -> None:
        r = ConvertResponse(
            task_id="task_abc123",
            status="completed",
            message="Done",
            yaml_content="title: T",
        )
        assert r.task_id == "task_abc123"
        assert r.status == "completed"

    def test_task_status(self) -> None:
        ts = TaskStatus(task_id="task_1", status="processing", progress=50.0)
        assert ts.progress == 50.0

    def test_upload_response(self) -> None:
        r = UploadResponse(task_id="t1", filename="novel.txt", char_count=1000, language="en")
        assert r.char_count == 1000

    def test_import_edits_response(self) -> None:
        r = ImportEditsResponse(
            task_id="t1",
            status="validated",
            validated=True,
            repaired_yaml="title: X",
            changes=["title"],
        )
        assert r.validated

    def test_alignment_response(self) -> None:
        r = AlignmentResponse(task_id="t1")
        assert r.original_text_alignment == []

    def test_validate_response(self) -> None:
        r = ValidateResponse(valid=True, errors=[], warnings=["No characters"])
        assert r.valid
        assert len(r.warnings) == 1

    def test_validate_response_invalid(self) -> None:
        r = ValidateResponse(valid=False, errors=["Missing title"])
        assert not r.valid

    def test_usage_stats(self) -> None:
        s = UsageStats(total_llm_calls=5, total_tokens=1000, total_cost_estimate=0.02)
        assert s.total_llm_calls == 5

    def test_detect_language_response(self) -> None:
        r = DetectLanguageResponse(language="chinese", confidence=0.95)
        assert r.language == "chinese"

    def test_health_response(self) -> None:
        r = HealthResponse(status="ok", version="2.0.0")
        assert r.status == "ok"
