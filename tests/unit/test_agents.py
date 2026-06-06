from __future__ import annotations

import json
from typing import Any

import pytest

from backend.agents.base import AgentBase
from backend.agents.narrative import NarrativeAgent
from backend.agents.character import CharacterAgent
from backend.agents.world import WorldAgent
from backend.agents.timeline import TimelineAgent
from backend.agents.episode_planner import EpisodePlannerAgent
from backend.agents.scene_planner import ScenePlannerAgent
from backend.agents.dialogue import DialogueAgent
from backend.agents.critic import CriticAgent
from backend.agents.repair import RepairAgent
from backend.agents.consistency import ConsistencyAgent


# ---------------------------------------------------------------------------
# MockLLMClient — returns appropriate JSON based on prompt content
# ---------------------------------------------------------------------------

class MockLLMClient:
    def __init__(self, custom_json: dict[str, Any] | None = None) -> None:
        self._custom = custom_json
        self._chat_calls: list[dict[str, Any]] = []

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: dict[str, str] | None = None,
    ) -> str:
        self._chat_calls.append({"messages": messages, "model": model, "temperature": temperature})
        if self._custom is not None:
            return json.dumps(self._custom, ensure_ascii=False)

        full = " ".join(m.get("content", "") for m in messages)
        return self._detect_and_respond(full)

    def extract_json(self, text: str) -> dict[str, Any]:
        if self._custom is not None:
            return dict(self._custom)
        return json.loads(text) if text.strip() else {}

    def repair_json(self, text: str) -> str:
        return text

    @staticmethod
    def _detect_and_respond(prompt: str) -> str:
        if "repaired_yaml" in prompt and "repair" in prompt.lower():
            return json.dumps(_MOCK_REPAIR, ensure_ascii=False)
        if "Score each category 0-10" in prompt or "quality assessment" in prompt:
            return json.dumps(_MOCK_CRITIC, ensure_ascii=False)
        if "Write dialogue and action beats" in prompt:
            return json.dumps(_MOCK_DIALOGUE, ensure_ascii=False)
        if "Plan individual scenes for episode" in prompt:
            return json.dumps(_MOCK_SCENE_PLANNER, ensure_ascii=False)
        if "Plan a TV series adaptation" in prompt:
            return json.dumps(_MOCK_EPISODE_PLANNER, ensure_ascii=False)
        if "timeline of events for screenplay" in prompt:
            return json.dumps(_MOCK_TIMELINE, ensure_ascii=False)
        if "world-building details" in prompt or "world-building specialist" in prompt:
            return json.dumps(_MOCK_WORLD, ensure_ascii=False)
        if "character analyst" in prompt or "identify all characters" in prompt:
            return json.dumps(_MOCK_CHARACTER, ensure_ascii=False)
        if "narrative structure" in prompt or "screenplay analyst" in prompt:
            return json.dumps(_MOCK_NARRATIVE, ensure_ascii=False)
        if "consistency" in prompt.lower() or "Compare the edited screenplay" in prompt:
            return json.dumps(_MOCK_CONSISTENCY, ensure_ascii=False)
        return "{}"


# ---------------------------------------------------------------------------
# Mock memory with semantic stub
# ---------------------------------------------------------------------------

class MockSemanticMemory:
    def retrieve_context(self, query: str, top_k: int = 3, max_chars: int = 3000) -> str:
        return ""

    def index_chunks(self, chunks: list[str], ids: list[str], metadatas: list[dict[str, Any]]) -> None:
        pass


class MockMemory:
    def __init__(self) -> None:
        self.semantic = MockSemanticMemory()


# ---------------------------------------------------------------------------
# Mock JSON data for each agent
# ---------------------------------------------------------------------------

_MOCK_NARRATIVE: dict[str, Any] = {
    "title": "命运之轮",
    "logline": "程序员林峰发现自己的代码能改变现实。",
    "genre": "科幻悬疑",
    "theme": "科技与人性的边界",
    "core_conflict": "林峰与控制世界代码的神秘组织K之间的对抗",
    "tone": "悬疑紧张，偶有温情",
    "target_audience": "25-40岁科幻爱好者",
    "style_notes": "冷色调，手持摄影，快速剪辑",
}

_MOCK_CHARACTER: dict[str, Any] = {
    "characters": [
        {
            "id": "char_001",
            "name": "林峰",
            "role": "protagonist",
            "goal": "找到控制能力的方法",
            "fear": "失去自我",
            "arc": "从逃避到承担",
            "voice_style": "内敛理性",
        },
        {
            "id": "char_002",
            "name": "苏瑶",
            "role": "supporting",
            "goal": "查明真相",
            "fear": "被控制",
            "arc": "从不信任到盟友",
            "voice_style": "冷静果断",
        },
    ],
}

_MOCK_WORLD: dict[str, Any] = {
    "locations": [
        {
            "name": "科技公司办公室",
            "description": "深夜的开放式办公区",
            "significance": "林峰发现秘密的地方",
            "visual_suggestions": "蓝色调的荧光灯照明",
        },
    ],
    "world_rules": [
        {
            "rule": "代码修改能影响现实",
            "implications": "每次修改都有蝴蝶效应",
            "visual_representation": "代码流动的视觉效果",
        },
    ],
    "atmosphere": "科技感与不安交织",
}

_MOCK_TIMELINE: dict[str, Any] = {
    "events": [
        {
            "order": 1,
            "description": "林峰加班发现代码异常",
            "characters_involved": ["林峰"],
            "location": "办公室",
            "emotional_beat": "震惊",
            "estimated_screen_time": 5,
        },
        {
            "order": 2,
            "description": "林峰验证自己的能力",
            "characters_involved": ["林峰"],
            "location": "公寓",
            "emotional_beat": "恐惧",
            "estimated_screen_time": 4,
        },
    ],
    "timeline_type": "linear",
    "major_turning_points": ["发现能力", "遇到K"],
}

_MOCK_EPISODE_PLANNER: dict[str, Any] = {
    "episodes": [
        {
            "id": "ep_001",
            "title": "代码里的世界",
            "summary": "林峰发现代码能改变现实。",
            "key_events": ["发现能力", "验证能力"],
            "characters_featured": ["林峰"],
            "emotional_arc": "从震惊到恐惧",
            "cliffhanger": "神秘人出现",
        },
    ],
    "season_arc": "林峰从逃避到接受命运的旅程",
}

_MOCK_SCENE_PLANNER: dict[str, Any] = {
    "episode_id": "ep_001",
    "scenes": [
        {
            "scene_id": "sc_001",
            "location": "科技公司办公室",
            "time": "凌晨2点",
            "visual_focus": "屏幕代码",
            "sound_effect": "键盘声",
            "voice_over": None,
            "transition": "cut",
            "duration_estimate": 120,
            "beats": [
                {"type": "action", "content": "林峰敲键盘", "emotion": "紧张"},
                {"type": "dialogue", "character_id": "char_001", "content": "这不可能...", "emotion": "震惊"},
            ],
        },
    ],
}

_MOCK_DIALOGUE: dict[str, Any] = {
    "beats": [
        {"type": "action", "content": "林峰盯着屏幕", "emotion": "紧张"},
        {"type": "dialogue", "character_id": "char_001", "content": "这不可能...", "emotion": "震惊"},
        {"type": "reaction", "character_id": "char_001", "content": "他揉了揉眼睛", "emotion": "恐惧"},
        {"type": "silence", "content": "办公室只剩空调声", "emotion": None},
    ],
}

_MOCK_CRITIC: dict[str, Any] = {
    "score": 7.5,
    "issues": [
        {
            "severity": "minor",
            "category": "pacing",
            "description": "第二幕节奏略快",
            "location": "ep_001/sc_002",
            "suggestion": "增加过渡场景",
        },
    ],
    "suggestions": ["增强苏瑶的角色深度", "增加反转"],
    "overall_assessment": "整体结构良好，角色鲜明，建议加强中段节奏。",
}

_MOCK_REPAIR: dict[str, Any] = {
    "repaired_yaml": "title: 命运之轮\nlogline: 程序员林峰发现自己的代码能改变现实。\ngenre: 科幻悬疑\ntheme: 科技与人性的边界",
    "changes_made": [
        {"field": "transition", "before": "jump_cut", "after": "cut", "reason": "Invalid transition type"},
    ],
    "validation_passed": True,
}

_MOCK_CONSISTENCY: dict[str, Any] = {
    "consistent": True,
    "issues": [],
    "resolved": True,
}

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_llm() -> MockLLMClient:
    return MockLLMClient()


@pytest.fixture
def mock_memory() -> MockMemory:
    return MockMemory()


# ---------------------------------------------------------------------------
# Test AgentBase abstract
# ---------------------------------------------------------------------------

class TestAgentBase:
    def test_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            AgentBase(None, None)  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# Test NarrativeAgent
# ---------------------------------------------------------------------------

class TestNarrativeAgent:
    def test_run_returns_valid(self, mock_llm: MockLLMClient, mock_memory: MockMemory) -> None:
        agent = NarrativeAgent(mock_llm, mock_memory)
        result = agent.run({"novel_text": "程序员林峰发现代码能改变现实。"})
        assert "title" in result
        assert "logline" in result
        assert result["title"] == "命运之轮"

    def test_validate_success(self, mock_llm: MockLLMClient, mock_memory: MockMemory) -> None:
        agent = NarrativeAgent(mock_llm, mock_memory)
        assert agent.validate(_MOCK_NARRATIVE)

    def test_validate_failure(self, mock_llm: MockLLMClient, mock_memory: MockMemory) -> None:
        agent = NarrativeAgent(mock_llm, mock_memory)
        assert not agent.validate({"title": "Only title"})

    def test_validate_with_errors(self, mock_llm: MockLLMClient, mock_memory: MockMemory) -> None:
        agent = NarrativeAgent(mock_llm, mock_memory)
        errors = agent.validate_with_errors({"title": "T"})
        assert len(errors) > 0


# ---------------------------------------------------------------------------
# Test CharacterAgent
# ---------------------------------------------------------------------------

class TestCharacterAgent:
    def test_validate_success(self, mock_llm: MockLLMClient, mock_memory: MockMemory) -> None:
        agent = CharacterAgent(mock_llm, mock_memory)
        assert agent.validate(_MOCK_CHARACTER)

    def test_validate_failure_empty(self, mock_llm: MockLLMClient, mock_memory: MockMemory) -> None:
        agent = CharacterAgent(mock_llm, mock_memory)
        assert not agent.validate({"characters": []})

    def test_validate_failure_missing_field(self, mock_llm: MockLLMClient, mock_memory: MockMemory) -> None:
        agent = CharacterAgent(mock_llm, mock_memory)
        assert not agent.validate({"characters": [{"id": "char_001", "name": "X"}]})

    def test_run_returns_valid(self, mock_llm: MockLLMClient, mock_memory: MockMemory) -> None:
        agent = CharacterAgent(mock_llm, mock_memory)
        result = agent.run({"novel_text": "测试文本"})
        assert "characters" in result
        assert isinstance(result["characters"], list)
        assert len(result["characters"]) == 2


# ---------------------------------------------------------------------------
# Test WorldAgent
# ---------------------------------------------------------------------------

class TestWorldAgent:
    def test_default_context(self, mock_llm: MockLLMClient, mock_memory: MockMemory) -> None:
        agent = WorldAgent(mock_llm, mock_memory)
        result = agent.run({"novel_text": "test"})
        assert "locations" in result

    def test_validate_success(self, mock_llm: MockLLMClient, mock_memory: MockMemory) -> None:
        agent = WorldAgent(mock_llm, mock_memory)
        assert agent.validate(_MOCK_WORLD)

    def test_validate_no_data(self, mock_llm: MockLLMClient, mock_memory: MockMemory) -> None:
        agent = WorldAgent(mock_llm, mock_memory)
        errors = agent.validate_with_errors({"locations": [], "world_rules": []})
        assert len(errors) > 0


# ---------------------------------------------------------------------------
# Test TimelineAgent
# ---------------------------------------------------------------------------

class TestTimelineAgent:
    def test_validate_success(self, mock_llm: MockLLMClient, mock_memory: MockMemory) -> None:
        agent = TimelineAgent(mock_llm, mock_memory)
        assert agent.validate(_MOCK_TIMELINE)

    def test_validate_empty_events(self, mock_llm: MockLLMClient, mock_memory: MockMemory) -> None:
        agent = TimelineAgent(mock_llm, mock_memory)
        assert not agent.validate({"events": []})

    def test_long_mode_validate(self, mock_llm: MockLLMClient, mock_memory: MockMemory) -> None:
        agent = TimelineAgent(mock_llm, mock_memory)
        result = agent.run({"novel_text": "test", "characters": [], "narrative": {}})
        assert agent.validate(result)


# ---------------------------------------------------------------------------
# Test ScenePlannerAgent
# ---------------------------------------------------------------------------

class TestScenePlannerAgent:
    def test_min_scenes(self, mock_llm: MockLLMClient, mock_memory: MockMemory) -> None:
        agent = ScenePlannerAgent(mock_llm, mock_memory)
        result = agent.run({
            "novel_text": "test",
            "episodes": [{"id": "ep_001", "title": "E1", "summary": "Test"}],
            "characters": [],
            "world": {},
            "current_episode_id": "ep_001",
        })
        assert "scenes" in result

    def test_validate_success(self, mock_llm: MockLLMClient, mock_memory: MockMemory) -> None:
        agent = ScenePlannerAgent(mock_llm, mock_memory)
        assert agent.validate(_MOCK_SCENE_PLANNER)

    def test_validate_no_episode_id(self, mock_llm: MockLLMClient, mock_memory: MockMemory) -> None:
        agent = ScenePlannerAgent(mock_llm, mock_memory)
        errors = agent.validate_with_errors({"scenes": [{"scene_id": "sc_001", "location": "X"}]})
        assert any("episode_id" in e for e in errors)

    def test_many_scenes(self, mock_llm: MockLLMClient, mock_memory: MockMemory) -> None:
        custom = {
            "episode_id": "ep_001",
            "scenes": [
                {"scene_id": f"sc_{i:03d}", "location": f"Loc{i}", "time": "Day", "transition": "cut",
                 "duration_estimate": 60, "beats": [{"type": "action", "content": "x"}]}
                for i in range(1, 11)
            ],
        }
        llm = MockLLMClient(custom_json=custom)
        agent = ScenePlannerAgent(llm, mock_memory)
        result = agent.run({"novel_text": "test", "episodes": [{"id": "ep_001"}], "characters": [], "world": {}})
        assert len(result["scenes"]) == 10


# ---------------------------------------------------------------------------
# Test EpisodePlannerAgent
# ---------------------------------------------------------------------------

class TestEpisodePlannerAgent:
    def test_validate_success(self, mock_llm: MockLLMClient, mock_memory: MockMemory) -> None:
        agent = EpisodePlannerAgent(mock_llm, mock_memory)
        assert agent.validate(_MOCK_EPISODE_PLANNER)

    def test_validate_no_season_arc(self, mock_llm: MockLLMClient, mock_memory: MockMemory) -> None:
        agent = EpisodePlannerAgent(mock_llm, mock_memory)
        assert not agent.validate({"episodes": [{"id": "ep_001", "title": "T", "summary": "S"}]})

    def test_run_returns_valid(self, mock_llm: MockLLMClient, mock_memory: MockMemory) -> None:
        agent = EpisodePlannerAgent(mock_llm, mock_memory)
        result = agent.run({"novel_text": "test", "timeline": {}, "narrative": {}, "target_episodes": 3})
        assert "episodes" in result
        assert "season_arc" in result


# ---------------------------------------------------------------------------
# Test DialogueWriterAgent
# ---------------------------------------------------------------------------

class TestDialogueWriterAgent:
    def test_beats_validation(self, mock_llm: MockLLMClient, mock_memory: MockMemory) -> None:
        agent = DialogueAgent(mock_llm, mock_memory)
        assert agent.validate(_MOCK_DIALOGUE)

    def test_invalid_beat_type(self, mock_llm: MockLLMClient, mock_memory: MockMemory) -> None:
        agent = DialogueAgent(mock_llm, mock_memory)
        assert not agent.validate({"beats": [{"type": "singing", "content": "x"}]})

    def test_missing_content(self, mock_llm: MockLLMClient, mock_memory: MockMemory) -> None:
        agent = DialogueAgent(mock_llm, mock_memory)
        assert not agent.validate({"beats": [{"type": "dialogue", "content": ""}]})


# ---------------------------------------------------------------------------
# Test CriticAgent
# ---------------------------------------------------------------------------

class TestCriticAgent:
    def test_score_range(self, mock_llm: MockLLMClient, mock_memory: MockMemory) -> None:
        agent = CriticAgent(mock_llm, mock_memory)
        result = agent.run({"yaml_content": "test", "original_text": "test", "characters": []})
        assert 0.0 <= result.get("score", 0) <= 10.0

    def test_validate_success(self, mock_llm: MockLLMClient, mock_memory: MockMemory) -> None:
        agent = CriticAgent(mock_llm, mock_memory)
        assert agent.validate(_MOCK_CRITIC)

    def test_validate_missing_score(self, mock_llm: MockLLMClient, mock_memory: MockMemory) -> None:
        agent = CriticAgent(mock_llm, mock_memory)
        assert not agent.validate({"issues": []})


# ---------------------------------------------------------------------------
# Test RepairAgent
# ---------------------------------------------------------------------------

class TestRepairAgent:
    def test_validate_success(self, mock_llm: MockLLMClient, mock_memory: MockMemory) -> None:
        agent = RepairAgent(mock_llm, mock_memory)
        assert agent.validate(_MOCK_REPAIR)

    def test_validate_short_yaml(self, mock_llm: MockLLMClient, mock_memory: MockMemory) -> None:
        agent = RepairAgent(mock_llm, mock_memory)
        assert not agent.validate({"repaired_yaml": "short"})

    def test_run_returns_valid(self, mock_llm: MockLLMClient, mock_memory: MockMemory) -> None:
        agent = RepairAgent(mock_llm, mock_memory)
        result = agent.run({
            "yaml_content": "test",
            "issues": [],
            "suggestions": [],
            "original_text": "test",
        })
        assert "repaired_yaml" in result


# ---------------------------------------------------------------------------
# Test ConsistencyAgent
# ---------------------------------------------------------------------------

class TestConsistencyAgent:
    def test_validate_success(self, mock_llm: MockLLMClient, mock_memory: MockMemory) -> None:
        agent = ConsistencyAgent(mock_llm, mock_memory)
        assert agent.validate(_MOCK_CONSISTENCY)

    def test_alignment_score_like(self, mock_llm: MockLLMClient, mock_memory: MockMemory) -> None:
        agent = ConsistencyAgent(mock_llm, mock_memory)
        result = agent.run({
            "original_chunks": ["chunk1"],
            "edited_yaml": "test",
            "original_text": "test",
        })
        assert "consistent" in result
        assert isinstance(result["consistent"], bool)

    def test_validate_missing_consistent(self, mock_llm: MockLLMClient, mock_memory: MockMemory) -> None:
        agent = ConsistencyAgent(mock_llm, mock_memory)
        assert not agent.validate({"issues": []})
