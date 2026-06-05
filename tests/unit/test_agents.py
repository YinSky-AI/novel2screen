"""
Unit tests for Novel2Screen agents.
"""
import json
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.agents.narrative import NarrativeAgent
from backend.agents.character import CharacterAgent
from backend.agents.world import WorldAgent
from backend.agents.timeline import TimelineAgent
from backend.agents.episode_planner import EpisodePlannerAgent
from backend.agents.scene_planner import ScenePlannerAgent
from backend.agents.dialogue import DialogueAgent
from backend.agents.critic import CriticAgent
from backend.agents.repair import RepairAgent
from backend.agents.consistency import BidirectionalConsistencyAgent


class TestNarrativeAgent:
    def setup_method(self):
        self.agent = NarrativeAgent()

    def test_validate_valid_output(self):
        output = {
            "major_events": [{"chapter": 1, "description": "Hero arrives", "characters_involved": ["Hero"]}],
            "subplots": [{"name": "Romance", "description": "Love story", "related_characters": ["Hero", "Love"]}],
            "turning_points": [{"chapter": 3, "description": "Big twist", "impact": "Changes everything"}],
            "theme": "Good vs evil",
        }
        assert self.agent.validate(output) is True

    def test_validate_empty_events(self):
        output = {"major_events": [], "subplots": [], "turning_points": [], "theme": ""}
        assert self.agent.validate(output) is False

    def test_validate_missing_fields(self):
        output = {"major_events": []}
        assert self.agent.validate(output) is False


class TestCharacterAgent:
    def setup_method(self):
        self.agent = CharacterAgent()

    def test_validate_valid_output(self):
        output = {
            "characters": [
                {
                    "id": "char_001", "name": "John", "role": "protagonist",
                    "goal": "Save world", "fear": "Loss", "arc": "Growth",
                    "voice_style": "Direct",
                }
            ]
        }
        assert self.agent.validate(output) is True

    def test_validate_no_characters(self):
        output = {"characters": []}
        assert self.agent.validate(output) is False


class TestWorldAgent:
    def setup_method(self):
        self.agent = WorldAgent()

    def test_validate_valid_output(self):
        output = {
            "world_rules": [{"domain": "magic", "description": "Fire magic"}],
            "geography": [{"name": "City", "description": "Big city", "significance": "Main"}],
        }
        assert self.agent.validate(output) is True

    def test_default_context(self):
        ctx = self.agent.get_default_context()
        assert "world_rules" in ctx
        assert "geography" in ctx


class TestTimelineAgent:
    def setup_method(self):
        self.agent = TimelineAgent()

    def test_validate_valid_short_output(self):
        output = {
            "events": [
                {"chapter": 1, "description": "Opening"},
                {"chapter": 2, "description": "Conflict"},
            ]
        }
        assert self.agent.validate(output) is True

    def test_validate_empty_events(self):
        output = {"events": []}
        assert self.agent.validate(output) is False


class TestEpisodePlannerAgent:
    def setup_method(self):
        self.agent = EpisodePlannerAgent()

    def test_validate_valid_output(self):
        output = {
            "episodes": [
                {"id": "ep_001", "title": "Pilot", "summary": "Beginning"}
            ]
        }
        assert self.agent.validate(output) is True

    def test_validate_no_episodes(self):
        output = {"episodes": []}
        assert self.agent.validate(output) is False


class TestScenePlannerAgent:
    def setup_method(self):
        self.agent = ScenePlannerAgent()

    def test_validate_valid_output(self):
        output = {
            "scenes": [
                {
                    "scene_id": "sc_001", "location": "Park", "time": "Morning",
                    "objective": "Meet", "conflict": "Disagreement", "emotion": "tension",
                }
            ]
        }
        assert self.agent.validate(output) is True

    def test_validate_no_scenes(self):
        output = {"scenes": []}
        assert self.agent.validate(output) is False


class TestDialogueAgent:
    def setup_method(self):
        self.agent = DialogueAgent()

    def test_validate_valid_output(self):
        output = {
            "scene_id": "sc_001",
            "location": "Cafe",
            "time": "Afternoon",
            "beats": [
                {"type": "action", "content": "Hero enters.", "emotion": None},
                {"type": "dialogue", "character_id": "char_001", "content": "Hello.", "emotion": "calm"},
            ],
            "transition": "cut",
            "duration_estimate": "60s",
        }
        assert self.agent.validate(output) is True

    def test_validate_too_few_beats(self):
        output = {
            "scene_id": "sc_001", "location": "X", "time": "X",
            "beats": [{"type": "action", "content": "X.", "emotion": None}],
            "transition": "cut", "duration_estimate": "10s",
        }
        assert self.agent.validate(output) is False


class TestCriticAgent:
    def setup_method(self):
        self.agent = CriticAgent()

    def test_validate_valid_output(self):
        output = {
            "violations": [
                {"category": "pacing", "severity": "warning", "description": "Too fast", "location": "sc_001"}
            ],
            "score": 0.85,
        }
        assert self.agent.validate(output) is True

    def test_get_quality_score(self):
        output = {"violations": [], "score": 0.95}
        assert self.agent.get_quality_score(output) == 0.95


class TestRepairAgent:
    def setup_method(self):
        self.agent = RepairAgent()

    def test_validate_non_empty_yaml(self):
        output = {"yaml_output": "title: Test"}
        assert self.agent.validate(output) is True

    def test_validate_empty_yaml(self):
        output = {"yaml_output": ""}
        assert self.agent.validate(output) is False


class TestConsistencyAgent:
    def setup_method(self):
        self.agent = BidirectionalConsistencyAgent()

    def test_validate_valid_output(self):
        output = {
            "alignment_score": 0.85,
            "deviations": ["Missing scene X"],
            "suggestions": ["Add scene X back"],
        }
        assert self.agent.validate(output) is True

    def test_validate_invalid_score(self):
        output = {
            "alignment_score": 1.5,
            "deviations": [],
            "suggestions": [],
        }
        assert self.agent.validate(output) is False
