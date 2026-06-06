from __future__ import annotations

from backend.schemas.models import (
    BeatType,
    CharacterOutput,
    CharacterRole,
    ConvertRequest,
    NarrativeOutput,
    ScenePlannerOutput,
    Transition,
)


class TestEnumValues:
    def test_all_character_roles_valid(self) -> None:
        for val in ("protagonist", "antagonist", "supporting"):
            role = CharacterRole(val)
            assert role.value == val

    def test_all_beat_types_valid(self) -> None:
        for val in ("dialogue", "action", "silence", "reaction"):
            bt = BeatType(val)
            assert bt.value == val

    def test_all_transitions_valid(self) -> None:
        for val in ("cut", "fade", "dissolve", "wipe"):
            t = Transition(val)
            assert t.value == val


class TestAgentOutputDefaults:
    def test_narrative_output_defaults(self) -> None:
        o = NarrativeOutput(
            title="T",
            logline="L",
            genre="G",
            theme="Th",
            core_conflict="C",
        )
        assert o.tone == ""
        assert o.target_audience == ""
        assert o.style_notes == ""

    def test_convert_request_defaults(self) -> None:
        r = ConvertRequest(novel_text="Once upon a time...")
        assert r.mode == "auto"
        assert r.pipeline == "full"
