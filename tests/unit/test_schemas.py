"""Unit tests for Novel2Screen Pydantic schemas and YAML validation."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.schemas.models import (
    Beat,
    Character,
    ConsistencyOutput,
    Episode,
    NarrativeOutput,
    Scene,
    Screenplay,
    Violation,
)
from backend.schemas.validator import screenplay_to_yaml, validate_screenplay_yaml, yaml_to_screenplay


class TestPydanticModels:
    def test_character_valid(self):
        c = Character(
            id="char_001", name="Hero", role="protagonist",
            goal="Save world", arc="Growth", fear="Loss",
        )
        assert c.id == "char_001"

    def test_character_invalid_id(self):
        with pytest.raises(Exception):
            Character(id="bad_id", name="X", role="protagonist", goal="X", arc="X")

    def test_beat_valid(self):
        b = Beat(type="dialogue", character_id="char_001", content="Hello", emotion="calm")
        assert b.type == "dialogue"

    def test_scene_valid(self):
        s = Scene(
            scene_id="sc_001", location="Park", time="Morning",
            beats=[Beat(type="action", content="Enter.", emotion=None)],
        )
        assert s.scene_id == "sc_001"

    def test_scene_empty_beats(self):
        with pytest.raises(Exception):
            Scene(scene_id="sc_001", location="X", time="X", beats=[])

    def test_episode_valid(self):
        e = Episode(
            id="ep_001", title="Pilot", summary="Start",
            scenes=[Scene(
                scene_id="sc_001", location="X", time="X",
                beats=[Beat(type="action", content="Y", emotion=None)],
            )],
        )
        assert e.id == "ep_001"

    def test_screenplay_empty_characters(self):
        with pytest.raises(Exception):
            Screenplay(title="Test", logline="L", genre="Drama", theme="T", characters=[], episodes=[])

    def test_screenplay_complete(self):
        sp = Screenplay(
            title="Test", logline="A story", genre="Drama", theme="Hope",
            characters=[Character(id="char_001", name="Hero", role="protagonist", goal="Win", arc="Grow")],
            episodes=[Episode(
                id="ep_001", title="Pilot", summary="Start",
                scenes=[Scene(
                    scene_id="sc_001", location="X", time="X",
                    beats=[Beat(type="action", content="Y", emotion=None)],
                )],
            )],
        )
        assert sp.title == "Test"
        assert len(sp.episodes) == 1

    def test_narrative_output_valid(self):
        no = NarrativeOutput(
            major_events=[{"chapter": 1, "description": "X", "characters_involved": ["A"]}],
            subplots=[{"name": "S", "description": "D", "related_characters": ["A"]}],
            turning_points=[{"chapter": 2, "description": "T", "impact": "Big"}],
            theme="Test",
        )
        assert no.theme == "Test"

    def test_violation_valid(self):
        v = Violation(category="pacing", severity="warning", description="Fast", location="sc_001")
        assert v.severity == "warning"

    def test_consistency_output_valid(self):
        co = ConsistencyOutput(alignment_score=0.8, deviations=["X"], suggestions=["Y"])
        assert co.alignment_score == 0.8

    def test_consistency_output_invalid_score(self):
        with pytest.raises(Exception):
            ConsistencyOutput(alignment_score=1.5, deviations=[], suggestions=[])


class TestYAMLValidation:
    def test_valid_yaml(self):
        sp = Screenplay(
            title="Test", logline="L", genre="Drama", theme="T",
            characters=[Character(id="char_001", name="A", role="protagonist", goal="G", arc="Arc")],
            episodes=[Episode(
                id="ep_001", title="Ep1", summary="S",
                scenes=[Scene(
                    scene_id="sc_001", location="L", time="T",
                    beats=[Beat(type="action", content="C", emotion=None)],
                )],
            )],
        )
        yaml_str = screenplay_to_yaml(sp)
        valid, errors = validate_screenplay_yaml(yaml_str)
        assert valid is True, f"Errors: {errors}"

    def test_invalid_yaml_string(self):
        valid, _errors = validate_screenplay_yaml("::: not valid yaml :::")
        assert valid is False

    def test_empty_dict_yaml(self):
        valid, _errors = validate_screenplay_yaml("title: Test")
        assert valid is False

    def test_round_trip_yaml(self):
        sp = Screenplay(
            title="RoundTrip", logline="Test round trip", genre="SciFi", theme="AI",
            characters=[Character(id="char_001", name="Bot", role="protagonist", goal="Learn", arc="Grow")],
            episodes=[Episode(
                id="ep_001", title="Start", summary="Begins",
                scenes=[Scene(
                    scene_id="sc_001", location="Lab", time="Dawn",
                    beats=[Beat(type="dialogue", character_id="char_001", content="Hello", emotion="calm")],
                    transition="fade", duration_estimate="30s",
                )],
            )],
        )
        yaml_str = screenplay_to_yaml(sp)
        parsed = yaml_to_screenplay(yaml_str)
        assert parsed.title == "RoundTrip"
        assert len(parsed.characters) == 1
        assert parsed.episodes[0].scenes[0].beats[0].content == "Hello"
