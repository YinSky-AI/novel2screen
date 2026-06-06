from __future__ import annotations

import json
import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest

from backend.harness.orchestrator import PipelineOrchestrator, PipelineState, build_fast_pipeline, build_full_pipeline, state_to_response
from backend.schemas.models import Screenplay
from backend.schemas.validator import _DEMO_SCREENPLAY_YAML, screenplay_to_yaml, validate_screenplay_yaml, yaml_to_screenplay
from backend.workflows.novel2screen import Novel2ScreenWorkflow


# ---------------------------------------------------------------------------
# Mock LLM that returns valid stage-appropriate JSON
# ---------------------------------------------------------------------------

_MOCK_CHARACTERS_JSON = json.dumps({
    "characters": [
        {"id": "char_001", "name": "Hero", "role": "protagonist", "goal": "Win", "fear": "Lose", "arc": "Growth", "voice_style": "bold"},
        {"id": "char_002", "name": "Villain", "role": "antagonist", "goal": "Destroy", "fear": "Nothing", "arc": "Fall", "voice_style": "cold"},
    ],
}, ensure_ascii=False)

_MOCK_EPISODE_PLANNER_JSON = json.dumps({
    "episodes": [
        {"id": "ep_001", "title": "Pilot", "summary": "Start", "key_events": ["e1"], "characters_featured": ["Hero"], "emotional_arc": "Hope", "cliffhanger": "???"},
        {"id": "ep_002", "title": "Rising", "summary": "Conflict", "key_events": ["e2"], "characters_featured": ["Hero", "Villain"], "emotional_arc": "Tension", "cliffhanger": "!!!"},
    ],
    "season_arc": "Hero wins",
}, ensure_ascii=False)


def _mock_llm_chat(messages: list[dict[str, str]], *, model: str = "", temperature: float = 0.7, **kwargs: Any) -> str:
    full = " ".join(m.get("content", "") for m in messages)

    if "timeline of events for screenplay" in full:
        return json.dumps({
            "events": [
                {"order": 1, "description": "Start", "characters_involved": ["Hero"], "location": "Home", "emotional_beat": "Hope", "estimated_screen_time": 5},
                {"order": 2, "description": "Conflict", "characters_involved": ["Hero", "Villain"], "location": "City", "emotional_beat": "Tension", "estimated_screen_time": 10},
            ],
            "timeline_type": "linear",
            "major_turning_points": ["The betrayal"],
        }, ensure_ascii=False)

    if "Plan a TV series adaptation" in full:
        return _MOCK_EPISODE_PLANNER_JSON

    if "Plan individual scenes for episode" in full:
        return json.dumps({
            "episode_id": "ep_001",
            "scenes": [
                {"scene_id": "sc_001", "location": "Home", "time": "Morning", "visual_focus": "Window", "sound_effect": "Wind", "voice_over": None, "transition": "cut", "duration_estimate": 60,
                 "beats": [{"type": "dialogue", "character_id": "char_001", "content": "Hello", "emotion": "hopeful"}]},
            ],
        }, ensure_ascii=False)

    if "character analyst" in full or "identify all characters" in full:
        return _MOCK_CHARACTERS_JSON

    if "world-building" in full or "world-building specialist" in full:
        return json.dumps({"locations": [{"name": "Home", "description": "A room", "significance": "Start", "visual_suggestions": "Warm light"}], "world_rules": [], "atmosphere": "Cozy"}, ensure_ascii=False)

    if "narrative structure" in full or "screenplay analyst" in full:
        return json.dumps({"title": "Test", "logline": "A test story.", "genre": "Drama", "theme": "Testing", "core_conflict": "Hero vs Villain", "tone": "Dark", "target_audience": "All", "style_notes": "Cinematic"}, ensure_ascii=False)

    if "Score each category" in full or "Quality assessment" in full:
        return json.dumps({"score": 8.0, "issues": [], "suggestions": [], "overall_assessment": "Good"}, ensure_ascii=False)

    if "repaired_yaml" in full or "Repair the following" in full:
        return json.dumps({"repaired_yaml": "title: Test", "changes_made": [], "validation_passed": True}, ensure_ascii=False)

    if "consistency" in full.lower() or "Compare the edited screenplay" in full:
        return json.dumps({"consistent": True, "issues": [], "resolved": True}, ensure_ascii=False)

    return "{}"


class MockLLM:
    def __init__(self) -> None:
        self._chat = _mock_llm_chat

    def chat(self, messages: list[dict[str, str]], *, model: str = "", temperature: float = 0.7, **kwargs: Any) -> str:
        return self._chat(messages, model=model, temperature=temperature, **kwargs)

    def extract_json(self, text: str) -> dict[str, Any]:
        return json.loads(text) if text.strip() else {}

    def repair_json(self, text: str) -> str:
        return text


class MockSettings:
    CHUNK_SIZE = 1500
    CHUNK_OVERLAP = 200


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestFastPipelineDemo:
    def test_fast_pipeline_demo(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "backend.core.preprocessor.chunk_paragraphs",
            lambda text, max_chars=500: [{"text": text[i:i+max_chars], "source": f"chunk_{i//max_chars+1}"} for i in range(0, len(text), max_chars)],
        )
        llm = MockLLM()
        memory = MagicMock()
        memory.semantic = MagicMock()
        memory.semantic.index_chunks = MagicMock()

        wf = Novel2ScreenWorkflow(MockSettings(), llm, memory)
        novel_text = "程序员林峰是一名普通的软件工程师。一天深夜，他在公司加班时发现了代码的秘密。"

        result = wf.fast_run(novel_text, mode="auto")

        assert result["status"] == "completed"
        assert result["task_id"].startswith("task_")
        assert len(result["yaml_content"]) > 0
        assert "title" in result["yaml_content"].lower()

    def test_full_pipeline_demo(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "backend.core.preprocessor.chunk_paragraphs",
            lambda text, max_chars=500: [{"text": text[i:i+max_chars], "source": f"chunk_{i//max_chars+1}"} for i in range(0, len(text), max_chars)],
        )
        llm = MockLLM()
        memory = MagicMock()
        memory.semantic = MagicMock()
        memory.semantic.index_chunks = MagicMock()
        memory.semantic.retrieve_context = MagicMock(return_value="")

        wf = Novel2ScreenWorkflow(MockSettings(), llm, memory)
        novel_text = "程序员林峰发现代码能改变现实。"

        result = wf.run(novel_text, mode="auto")

        assert result["status"] == "completed"
        assert len(result["yaml_content"]) > 0

    def test_demo_screenplay_valid(self) -> None:
        report = validate_screenplay_yaml(_DEMO_SCREENPLAY_YAML)
        assert report.valid
        assert len(report.errors) == 0

    def test_roundtrip(self) -> None:
        sp = yaml_to_screenplay(_DEMO_SCREENPLAY_YAML)
        yaml_str = screenplay_to_yaml(sp)
        sp2 = yaml_to_screenplay(yaml_str)

        assert sp2.title == sp.title
        assert len(sp2.characters) == len(sp.characters)
        assert len(sp2.episodes) == len(sp.episodes)

        for orig_ep, round_ep in zip(sp.episodes, sp2.episodes):
            assert round_ep.id == orig_ep.id
            assert len(round_ep.scenes) == len(orig_ep.scenes)

    def test_demo_yaml_parse_roundtrip_validates(self) -> None:
        sp = yaml_to_screenplay(_DEMO_SCREENPLAY_YAML)
        yaml_str = screenplay_to_yaml(sp)
        report = validate_screenplay_yaml(yaml_str)
        assert report.valid

    def test_orchestrator_build_fast_pipeline_state(self) -> None:
        llm = MockLLM()
        memory = MagicMock()
        memory.semantic = MagicMock()

        from backend.agents.narrative import NarrativeAgent
        from backend.agents.character import CharacterAgent
        from backend.agents.world import WorldAgent
        from backend.agents.timeline import TimelineAgent
        from backend.agents.episode_planner import EpisodePlannerAgent
        from backend.agents.scene_planner import ScenePlannerAgent

        agents = {
            "narrative": NarrativeAgent(llm, memory),
            "character": CharacterAgent(llm, memory),
            "world": WorldAgent(llm, memory),
            "timeline": TimelineAgent(llm, memory),
            "episode_planner": EpisodePlannerAgent(llm, memory),
            "scene_planner": ScenePlannerAgent(llm, memory),
        }

        orchestrator = PipelineOrchestrator(agents)
        state = PipelineState(novel_text="程序员林峰的故事。")
        state = build_fast_pipeline(orchestrator, state)

        assert state.screenplay is not None
        assert isinstance(state.screenplay, Screenplay)
        assert len(state.screenplay.episodes) > 0

    def test_orchestrator_build_full_pipeline_state(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from backend.agents.narrative import NarrativeAgent
        from backend.agents.character import CharacterAgent
        from backend.agents.world import WorldAgent
        from backend.agents.timeline import TimelineAgent
        from backend.agents.episode_planner import EpisodePlannerAgent
        from backend.agents.scene_planner import ScenePlannerAgent
        from backend.agents.critic import CriticAgent
        from backend.agents.repair import RepairAgent
        from backend.agents.consistency import ConsistencyAgent

        class FullMockLLM:
            def chat(self, messages: list[dict[str, str]], *, model: str = "", temperature: float = 0.7, **kwargs: Any) -> str:
                return _mock_llm_chat(messages, model=model, temperature=temperature, **kwargs)

            def extract_json(self, text: str) -> dict[str, Any]:
                return json.loads(text) if text.strip() else {}

            def repair_json(self, text: str) -> str:
                return text

        llm = FullMockLLM()
        memory = MagicMock()
        memory.semantic = MagicMock()
        memory.semantic.retrieve_context = MagicMock(return_value="")

        agents = {
            "narrative": NarrativeAgent(llm, memory),
            "character": CharacterAgent(llm, memory),
            "world": WorldAgent(llm, memory),
            "timeline": TimelineAgent(llm, memory),
            "episode_planner": EpisodePlannerAgent(llm, memory),
            "scene_planner": ScenePlannerAgent(llm, memory),
            "critic": CriticAgent(llm, memory),
            "repair": RepairAgent(llm, memory),
            "consistency": ConsistencyAgent(llm, memory),
        }

        orchestrator = PipelineOrchestrator(agents)
        state = PipelineState(novel_text="程序员林峰的故事。")
        state = build_full_pipeline(orchestrator, state)

        assert state.screenplay is not None
        assert len(state.episodes_plan.get("episodes", [])) > 0
        assert "consistent" in state.consistency

    def test_state_to_response(self) -> None:
        state = PipelineState(
            novel_text="test",
            yaml_content="title: Test",
            screenplay=Screenplay(title="Test", logline="A test", genre="Drama", theme="Test"),
        )
        response = state_to_response(state, "task_123")
        assert response.task_id == "task_123"
        assert response.status == "completed"
        assert response.yaml_content == "title: Test"

    def test_state_to_response_with_errors(self) -> None:
        state = PipelineState(
            novel_text="test",
            errors=["Something went wrong"],
        )
        response = state_to_response(state, "task_456")
        assert response.status == "error"
        assert "Something went wrong" in response.message

    def test_workflow_import_edits(self) -> None:
        wf = Novel2ScreenWorkflow(MockSettings(), MockLLM(), MagicMock())
        result = wf.import_edits("test_task", _DEMO_SCREENPLAY_YAML)
        assert result["task_id"] == "test_task"
        assert result["status"] in ("validated", "repaired", "validation_failed")

    def test_workflow_save_export(self, tmp_path: Any) -> None:
        import os
        original_dir = os.getcwd()
        try:
            os.chdir(str(tmp_path))
            wf = Novel2ScreenWorkflow(MockSettings(), MockLLM(), MagicMock())
            filepath = wf.save_export("task_export", _DEMO_SCREENPLAY_YAML)
            assert os.path.exists(filepath)
            with open(filepath, encoding="utf-8") as f:
                content = f.read()
            assert "命运之轮" in content
        finally:
            os.chdir(original_dir)
