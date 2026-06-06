from __future__ import annotations

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


class TestCharacterModel:
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
        assert c.fear == ""
        assert c.voice_style == ""

    def test_invalid_id_pattern_raises(self) -> None:
        with pytest.raises(Exception):
            Character(
                id="hero_1",
                name="Bad ID",
                role=CharacterRole.SUPPORTING,
                goal="test",
                arc="test",
            )


class TestBeatModel:
    def test_dialogue_beat_with_character_id(self) -> None:
        b = Beat(
            type=BeatType.DIALOGUE,
            character_id="char_001",
            content="Hello world",
            emotion="happy",
        )
        assert b.type == BeatType.DIALOGUE
        assert b.character_id == "char_001"


class TestSceneModel:
    def test_scene_with_beats(self) -> None:
        beats = [
            Beat(type=BeatType.DIALOGUE, character_id="char_001", content="Hi"),
            Beat(type=BeatType.SILENCE, content="Pause"),
        ]
        s = Scene(
            scene_id="sc_001",
            location="Park",
            time="Dawn",
            beats=beats,
            transition=Transition.FADE,
        )
        assert len(s.beats) == 2
        assert s.transition == Transition.FADE


class TestEpisodeModel:
    def test_invalid_episode_id_raises(self) -> None:
        with pytest.raises(Exception):
            Episode(id="bad", title="Bad", summary="No")


class TestScreenplayValidation:
    def test_screenplay_requires_characters_and_episodes(self) -> None:
        yaml_str = "title: Empty\nlogline: Nothing.\ngenre: Test\ntheme: Test\ncharacters: []\nepisodes: []\n"
        report = validate_screenplay_yaml(yaml_str)
        assert "No episodes defined" in report.errors or not report.valid


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

    def test_demo_yaml_is_valid(self) -> None:
        report = validate_screenplay_yaml(_DEMO_SCREENPLAY_YAML)
        assert report.valid
        assert len(report.errors) == 0
