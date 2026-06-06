from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

import pytest

from backend.agents.character import CharacterAgent
from backend.agents.episode_planner import EpisodePlannerAgent
from backend.agents.narrative import NarrativeAgent
from backend.agents.scene_planner import ScenePlannerAgent


class MockLLMClient:
    def __init__(self, custom_json: dict[str, Any] | None = None) -> None:
        self._custom = custom_json

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: dict[str, str] | None = None,
    ) -> str:
        if self._custom is not None:
            return json.dumps(self._custom, ensure_ascii=False)
        full = " ".join(m.get("content", "") for m in messages)
        return self._respond(full)

    def extract_json(self, text: str) -> dict[str, Any]:
        if self._custom is not None:
            return dict(self._custom)
        return json.loads(text) if text.strip() else {}

    def repair_json(self, text: str) -> str:
        return text

    @staticmethod
    def _respond(prompt: str) -> str:
        if "episode planner" in prompt.lower() or "Plan a TV series adaptation" in prompt:
            return json.dumps(_VALID_EPISODES, ensure_ascii=False)
        if "scene planner" in prompt.lower() or "Plan individual scenes for episode" in prompt:
            return json.dumps(_VALID_SCENES, ensure_ascii=False)
        if "character analyst" in prompt.lower() or "identify all characters" in prompt:
            return json.dumps(_VALID_CHARACTERS, ensure_ascii=False)
        if "screenplay analyst" in prompt.lower() or "narrative structure" in prompt:
            return json.dumps(_VALID_NARRATIVE, ensure_ascii=False)
        return "{}"


_VALID_NARRATIVE: dict[str, Any] = {
    "title": "命运之轮",
    "logline": "程序员林峰发现代码能改变现实。",
    "genre": "科幻悬疑",
    "theme": "科技与人性的边界",
    "major_events": [
        {"chapter": 1, "event": "林峰发现代码异常", "characters_involved": ["林峰"]},
    ],
    "subplots": [],
}

_VALID_CHARACTERS: dict[str, Any] = {
    "characters": [
        {"id": "char_001", "name": "林峰", "role": "protagonist", "goal": "找到控制能力的方法", "fear": "失去自我", "arc": "从逃避到承担", "voice_style": "内敛理性"},
        {"id": "char_002", "name": "苏瑶", "role": "supporting", "goal": "查明真相", "fear": "被控制", "arc": "从不信任到盟友", "voice_style": "冷静果断"},
    ],
}

_VALID_EPISODES: dict[str, Any] = {
    "episodes": [
        {"id": "ep_001", "title": "代码里的世界", "summary": "林峰发现代码能改变现实。"},
    ],
    "season_arc": "林峰的成长旅程",
}

_VALID_SCENES: dict[str, Any] = {
    "episode_id": "ep_001",
    "scenes": [
        {"scene_id": "sc_001", "location": "科技公司办公室", "time": "凌晨2点", "beats": [{"type": "action", "content": "林峰敲键盘", "emotion": "紧张"}]},
        {"scene_id": "sc_002", "location": "林峰公寓", "time": "凌晨4点", "beats": [{"type": "dialogue", "character_id": "char_001", "content": "这不可能...", "emotion": "震惊"}]},
        {"scene_id": "sc_003", "location": "咖啡馆", "time": "下午3点", "beats": [{"type": "reaction", "character_id": "char_001", "content": "林峰愣住了", "emotion": "困惑"}]},
    ],
}

_EMPTY_CHARACTERS: dict[str, Any] = {"characters": []}
_EMPTY_NARRATIVE: dict[str, Any] = {"title": "", "logline": "", "genre": "", "theme": "", "major_events": []}
_EMPTY_EPISODES: dict[str, Any] = {"episodes": [], "season_arc": ""}
_NO_SCENES: dict[str, Any] = {
    "episode_id": "ep_001",
    "scenes": [],
}

_MISSING_LOCATION: dict[str, Any] = {
    "episode_id": "ep_001",
    "scenes": [{"scene_id": "sc_001", "time": "Now", "beats": [{"type": "action", "content": "x"}]}],
}


@pytest.fixture
def mock_llm() -> MockLLMClient:
    return MockLLMClient()


@pytest.fixture
def mock_memory() -> MagicMock:
    m = MagicMock()
    m.semantic = MagicMock()
    m.semantic.retrieve_context = MagicMock(return_value="")
    return m


class TestNarrativeAgent:
    def test_validate_passes_with_valid_output(self, mock_llm: MockLLMClient, mock_memory: MagicMock) -> None:
        agent = NarrativeAgent(mock_llm, mock_memory)
        assert agent.validate(_VALID_NARRATIVE)

    def test_validate_fails_with_empty_events(self, mock_llm: MockLLMClient, mock_memory: MagicMock) -> None:
        agent = NarrativeAgent(mock_llm, mock_memory)
        assert not agent.validate(_EMPTY_NARRATIVE)

    def test_run_returns_expected_keys(self, mock_llm: MockLLMClient, mock_memory: MagicMock) -> None:
        agent = NarrativeAgent(mock_llm, mock_memory)
        result = agent.run({"novel_text": "测试文本"})
        for key in ("title", "logline", "genre", "theme", "major_events"):
            assert key in result


class TestCharacterAgent:
    def test_validate_passes_with_valid_characters(self, mock_llm: MockLLMClient, mock_memory: MagicMock) -> None:
        agent = CharacterAgent(mock_llm, mock_memory)
        assert agent.validate(_VALID_CHARACTERS)

    def test_validate_fails_with_no_characters(self, mock_llm: MockLLMClient, mock_memory: MagicMock) -> None:
        agent = CharacterAgent(mock_llm, mock_memory)
        assert not agent.validate(_EMPTY_CHARACTERS)

    def test_run_returns_characters_key(self, mock_llm: MockLLMClient, mock_memory: MagicMock) -> None:
        agent = CharacterAgent(mock_llm, mock_memory)
        result = agent.run({"novel_text": "测试文本"})
        assert "characters" in result
        assert isinstance(result["characters"], list)
        assert len(result["characters"]) == 2


class TestScenePlannerAgent:
    def test_validate_fails_with_no_scenes(self, mock_llm: MockLLMClient, mock_memory: MagicMock) -> None:
        agent = ScenePlannerAgent(mock_llm, mock_memory)
        assert not agent.validate(_NO_SCENES)

    def test_validate_fails_with_missing_location(self, mock_llm: MockLLMClient, mock_memory: MagicMock) -> None:
        agent = ScenePlannerAgent(mock_llm, mock_memory)
        assert not agent.validate(_MISSING_LOCATION)

    def test_validate_passes_with_valid_output(self, mock_llm: MockLLMClient, mock_memory: MagicMock) -> None:
        agent = ScenePlannerAgent(mock_llm, mock_memory)
        assert agent.validate(_VALID_SCENES)


class TestEpisodePlannerAgent:
    def test_validate_passes_with_valid_episodes(self, mock_llm: MockLLMClient, mock_memory: MagicMock) -> None:
        agent = EpisodePlannerAgent(mock_llm, mock_memory)
        assert agent.validate(_VALID_EPISODES)

    def test_validate_fails_with_empty_episodes(self, mock_llm: MockLLMClient, mock_memory: MagicMock) -> None:
        agent = EpisodePlannerAgent(mock_llm, mock_memory)
        assert not agent.validate(_EMPTY_EPISODES)
