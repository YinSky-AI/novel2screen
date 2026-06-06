#!/usr/bin/env python3
"""MCP stdin/stdout server for Novel2Screen.

Protocol: reads one JSON object per line from stdin, responds with one JSON
object per line to stdout.  All log messages go to stderr.

Actions:
  health      – health check
  info        – server metadata
  validate    – validate a YAML screenplay
  convert     – convert novel text (fast or full pipeline)
"""

from __future__ import annotations

import json
import sys
import traceback
from typing import Any


# ---------------------------------------------------------------
# Resolve paths so imports work from any working directory
# ---------------------------------------------------------------
def _resolve_imports() -> None:
    import os
    backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
    project_root = os.path.abspath(os.path.join(backend_root, ".."))
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)


_resolve_imports()

from backend.config import Settings
from backend.core.llm import LLMClient
from backend.core.memory import MemoryManager
from backend.schemas.validator import _DEMO_SCREENPLAY_YAML, validate_screenplay_yaml
from backend.workflows.novel2screen import Novel2ScreenWorkflow


# ---------------------------------------------------------------
# Server state
# ---------------------------------------------------------------
_settings = Settings()
_workflow: Novel2ScreenWorkflow | None = None


def _get_workflow() -> Novel2ScreenWorkflow:
    global _workflow
    if _workflow is None:
        _workflow = Novel2ScreenWorkflow(_settings, LLMClient(), MemoryManager())
    return _workflow


# ---------------------------------------------------------------
# Action handlers
# ---------------------------------------------------------------

def handle_health(params: dict[str, Any]) -> dict[str, Any]:
    return {"status": "ok", "version": "2.0.0", "action": "health"}


def handle_info(params: dict[str, Any]) -> dict[str, Any]:
    return {
        "action": "info",
        "name": "novel2screen-mcp-server",
        "version": "2.0.0",
        "description": "Convert novels to screenplays via LLM pipeline",
        "capabilities": ["convert", "validate", "health", "info"],
        "pipeline_modes": ["fast", "full"],
        "supported_languages": ["chinese", "english"],
    }


def handle_validate(params: dict[str, Any]) -> dict[str, Any]:
    yaml_content = params.get("yaml_content", "")
    if not yaml_content:
        return {"action": "validate", "valid": False, "errors": ["No yaml_content provided"], "warnings": []}

    report = validate_screenplay_yaml(yaml_content)
    return {
        "action": "validate",
        "valid": report.valid,
        "errors": report.errors,
        "warnings": report.warnings,
    }


def handle_convert(params: dict[str, Any]) -> dict[str, Any]:
    novel_text = params.get("novel_text", "")
    if not novel_text:
        return {"action": "convert", "status": "error", "message": "novel_text is required", "yaml_content": ""}

    pipeline = params.get("pipeline", "full")
    mode = params.get("mode", "auto")

    if mode == "demo":
        return {
            "action": "convert",
            "task_id": "demo",
            "status": "completed",
            "message": "Demo screenplay generated",
            "yaml_content": _DEMO_SCREENPLAY_YAML,
        }

    try:
        wf = _get_workflow()
        if pipeline == "fast":
            result = wf.fast_run(novel_text, mode)
        else:
            result = wf.run(novel_text, mode)

        return {
            "action": "convert",
            "task_id": result.task_id,
            "status": result.status,
            "message": result.message,
            "yaml_content": result.yaml_content,
        }
    except Exception as exc:
        return {
            "action": "convert",
            "status": "error",
            "message": f"{type(exc).__name__}: {exc}",
            "yaml_content": "",
        }


_ACTION_MAP: dict[str, Any] = {
    "health": handle_health,
    "info": handle_info,
    "validate": handle_validate,
    "convert": handle_convert,
}


# ---------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------

def _send(response: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _error(request_id: str | None, message: str) -> None:
    _send({"error": True, "message": message, "request_id": request_id})


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        request_id: str | None = None
        try:
            request = json.loads(line)
            request_id = request.get("request_id")
            action = request.get("action", "")

            if action not in _ACTION_MAP:
                _error(request_id, f"Unknown action: {action}. Supported: {list(_ACTION_MAP.keys())}")
                continue

            handler = _ACTION_MAP[action]
            result = handler(request.get("params", {}))
            result["request_id"] = request_id
            _send(result)

        except json.JSONDecodeError:
            _error(request_id, f"Invalid JSON input: {line[:200]}")
        except Exception:
            _error(request_id, traceback.format_exc())


if __name__ == "__main__":
    main()
