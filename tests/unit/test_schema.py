from __future__ import annotations

import json
from typing import Any

import pytest
import yaml

from backend.schemas.models import (
    Beat,
    BeatType,
    Character,
    CharacterRole,
    Episode,
    Scene,
    Screenplay,
    Transition,
)
from backend.schemas.validator import (
    _DEMO_SCREENPLAY_YAML,
    screenplay_to_yaml,
    validate_screenplay_yaml,
    yaml_to_screenplay,
)


class MockLLMClient:
    def chat(self, messages: list[dict[str, str]], *, model: str = "", temperature: float = 0.7) -> str:
        return "{}"

    def extract_json(self, text: str) -> dict[str, Any]:
        return json.loads(text) if text.strip() else {}

    def repair_json(self, text: str) -> str:
        return text


# ---------------------------------------------------------------------------
# Character model
# ---------------------------------------------------------------------------

class TestCharacter:
    def test_valid_character(self) -> None:
        c = Character(
            id="char_001",
            name="Lin Feng",
            role=CharacterRole.PROTAGONIST,
            goal="Save the world",
            arc="From zero to hero",
        )
        assert c.id == "char_001"
        assert c.role == CharacterRole.PROTAGONIST

    def test_invalid_character_id_pattern(self) -> None:
        with pytest.raises(Exception):
            Character(
                id="hero_1",
                name="Bad ID",
                role=CharacterRole.SUPPORTING,
                goal="test",
                arc="test",
            )

    def test_character_optional_fields(self) -> None:
        c = Character(
            id="char_042",
            name="Minimal",
            role=CharacterRole.ANTAGONIST,
            goal="Power",
            arc="Downfall",
        )
        assert c.fear == ""
        assert c.voice_style == ""


# ---------------------------------------------------------------------------
# Beat model
# ---------------------------------------------------------------------------

class TestBeat:
    def test_dialogue_beat(self) -> None:
        b = Beat(
            type=BeatType.DIALOGUE,
            character_id="char_001",
            content="Hello world",
            emotion="happy",
        )
        assert b.type == BeatType.DIALOGUE
        assert b.character_id == "char_001"

    def test_action_beat(self) -> None:
        b = Beat(type=BeatType.ACTION, content="He runs.")
        assert b.type == BeatType.ACTION
        assert b.character_id is None

    def test_silence_beat(self) -> None:
        b = Beat(type=BeatType.SILENCE, content="Silence fills the room.")
        assert b.type == BeatType.SILENCE

    def test_reaction_beat(self) -> None:
        b = Beat(
            type=BeatType.REACTION,
            character_id="char_002",
            content="She gasps.",
            emotion="shock",
        )
        assert b.type == BeatType.REACTION


# ---------------------------------------------------------------------------
# Scene model
# ---------------------------------------------------------------------------

class TestScene:
    def test_valid_scene(self) -> None:
        s = Scene(
            scene_id="sc_001",
            location="Office",
            time="Midnight",
            beats=[Beat(type=BeatType.ACTION, content="Typing.")],
        )
        assert s.scene_id == "sc_001"
        assert s.transition == Transition.CUT
        assert s.duration_estimate == 60

    def test_invalid_scene_id(self) -> None:
        with pytest.raises(Exception):
            Scene(scene_id="bad_id", location="Room", time="Now")

    def test_scene_with_multiple_beats(self) -> None:
        beats = [
            Beat(type=BeatType.DIALOGUE, character_id="char_001", content="Hi"),
            Beat(type=BeatType.SILENCE, content="Pause"),
            Beat(type=BeatType.REACTION, character_id="char_002", content="Nods"),
        ]
        s = Scene(scene_id="sc_005", location="Park", time="Dawn", beats=beats)
        assert len(s.beats) == 3


# ---------------------------------------------------------------------------
# Episode model
# ---------------------------------------------------------------------------

class TestEpisode:
    def test_valid_episode(self) -> None:
        ep = Episode(
            id="ep_001",
            title="Pilot",
            summary="The beginning.",
            scenes=[
                Scene(
                    scene_id="sc_001",
                    location="Home",
                    time="Morning",
                    beats=[Beat(type=BeatType.ACTION, content="Wake up.")],
                ),
            ],
        )
        assert ep.id == "ep_001"
        assert len(ep.scenes) == 1

    def test_invalid_episode_id(self) -> None:
        with pytest.raises(Exception):
            Episode(id="bad", title="Bad", summary="No")

    def test_episode_multiple_scenes(self) -> None:
        scenes = [
            Scene(scene_id="sc_001", location="A", time="Day", beats=[Beat(type=BeatType.ACTION, content="x")]),
            Scene(scene_id="sc_002", location="B", time="Night", beats=[Beat(type=BeatType.ACTION, content="y")]),
        ]
        ep = Episode(id="ep_003", title="Multi", summary="Two scenes", scenes=scenes)
        assert len(ep.scenes) == 2


# ---------------------------------------------------------------------------
# Screenplay roundtrip
# ---------------------------------------------------------------------------

class TestScreenplayRoundtrip:
    def test_yaml_roundtrip(self) -> None:
        original = Screenplay(
            title="Test",
            logline="A test.",
            genre="Drama",
            theme="Testing",
            characters=[
                Character(id="char_001", name="Tester", role=CharacterRole.PROTAGONIST, goal="Pass", arc="Growth"),
            ],
            episodes=[
                Episode(
                    id="ep_001",
                    title="E1",
                    summary="First ep",
                    scenes=[
                        Scene(
                            scene_id="sc_001",
                            location="Lab",
                            time="Now",
                            beats=[
                                Beat(type=BeatType.DIALOGUE, character_id="char_001", content="Testing...", emotion="focused"),
                                Beat(type=BeatType.SILENCE, content="Quiet"),
                            ],
                            transition=Transition.FADE,
                            duration_estimate=90,
                        ),
                    ],
                ),
            ],
        )
        yaml_str = screenplay_to_yaml(original)
        parsed = yaml_to_screenplay(yaml_str)
        assert parsed.title == original.title
        assert parsed.logline == original.logline
        assert len(parsed.characters) == 1
        assert len(parsed.episodes) == 1
        assert len(parsed.episodes[0].scenes) == 1
        assert len(parsed.episodes[0].scenes[0].beats) == 2

    def test_yaml_serialization_roundtrip(self) -> None:
        sp = Screenplay(
            title="Roundtrip",
            logline="Testing serialization.",
            genre="Test",
            theme="Roundtrip",
            characters=[
                Character(id="char_001", name="A", role=CharacterRole.PROTAGONIST, goal="Goal", arc="Arc"),
            ],
            episodes=[],
        )
        yaml_str = screenplay_to_yaml(sp)
        data = yaml.safe_load(yaml_str)
        assert data["title"] == "Roundtrip"
        assert len(data["characters"]) == 1
        assert data["characters"][0]["id"] == "char_001"

    def test_demo_yaml_valid(self) -> None:
        report = validate_screenplay_yaml(_DEMO_SCREENPLAY_YAML)
        assert report.valid
        assert len(report.errors) == 0

    def test_demo_yaml_parses(self) -> None:
        sp = yaml_to_screenplay(_DEMO_SCREENPLAY_YAML)
        assert sp.title == "命运之轮"
        assert len(sp.characters) == 3
        assert len(sp.episodes) == 2
        assert sp.episodes[0].scenes[0].beats[0].type == BeatType.ACTION
