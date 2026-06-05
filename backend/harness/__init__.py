"""Novel2Screen Harness: Stage-based pipeline orchestration.

Components:
  - orchestrator:  Pipeline state machine (fast / full)
  - novel_reader:  Language detection, chapter parsing, smart chunking
  - output_validator: Comprehensive YAML validation
"""
from .novel_reader import detect_language, get_emotion_set, parse_chapters
from .orchestrator import build_state, run_pipeline, state_to_response
from .output_validator import ValidationReport, validate_screenplay_output

__all__ = [
    "ValidationReport",
    "build_state",
    "detect_language",
    "get_emotion_set",
    "parse_chapters",
    "run_pipeline",
    "state_to_response",
    "validate_screenplay_output",
]
