"""Integration test: short mode with 3-chapter novel -> valid YAML."""
import sys, os, json, yaml
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
os.environ["OPENAI_API_KEY"] = ""
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["DEEPSEEK_API_KEY"] = ""

from backend.workflows.novel2screen import Novel2ScreenWorkflow
from backend.schemas.validator import validate_screenplay_yaml


def test_short_mode_integration():
    """3-chapter novel -> valid YAML in demo mode."""
    novel = """Chapter 1\nJohn walked into a dark bar. A stranger gave him a photograph.\nChapter 2\nThe photograph showed a building on fire - John's old office.\nChapter 3\nJohn found a hidden room with files about his past."""
    wf = Novel2ScreenWorkflow()
    state = wf.fast_run(novel_text=novel, novel_title="Test Novel", genre="Mystery", mode="short")
    assert state["completed"] is True, f"Pipeline failed: {state.get('error', '')}"
    assert state.get("screenplay_yaml", ""), "No YAML output"
    valid, errors = validate_screenplay_yaml(state["screenplay_yaml"])
    assert valid, f"Schema validation failed: {errors[:3]}"
    sp = state.get("screenplay", {})
    assert len(sp.get("episodes", [])) >= 1, "No episodes"
    assert len(sp.get("characters", [])) >= 1, "No characters"
    print(f"PASS: short_mode_integration (episodes={len(sp.get('episodes',[]))}, chars={len(sp.get('characters',[]))})")


def test_schema_roundtrip():
    """Export YAML -> parse -> serialize -> validate."""
    novel = """Chapter 1\nAlice found a key.\nChapter 2\nThe key opened a locked door.\nChapter 3\nBehind the door was the truth."""
    wf = Novel2ScreenWorkflow()
    state = wf.fast_run(novel_text=novel, novel_title="Roundtrip", genre="Drama", mode="short")
    yaml_str = state.get("screenplay_yaml", "")
    assert yaml_str, "No YAML from pipeline"
    data = yaml.safe_load(yaml_str)
    assert data, "YAML parse failed"
    assert "title" in data, "Missing title"
    assert "characters" in data, "Missing characters"
    assert "episodes" in data, "Missing episodes"
    valid, errors = validate_screenplay_yaml(yaml_str)
    assert valid, f"Roundtrip validation failed: {errors[:3]}"
    print("PASS: schema_roundtrip")


def test_pipeline_critic():
    """Pipeline produces valid critic output."""
    novel = """Chapter 1\nStart.\nChapter 2\nMiddle.\nChapter 3\nEnd."""
    wf = Novel2ScreenWorkflow()
    state = wf.fast_run(novel_text=novel, novel_title="CriticTest", genre="Drama", mode="short")
    assert "violations" in state, "Missing violations in state"
    assert "critic_score" in state, "Missing critic score"
    assert isinstance(state.get("critic_score"), (int, float)), "Score not numeric"
    print(f"PASS: pipeline_critic (violations={len(state.get('violations',[]))}, score={state.get('critic_score','?')})")


if __name__ == "__main__":
    test_short_mode_integration()
    test_schema_roundtrip()
    test_pipeline_critic()
    print("\nAll integration tests passed!")
