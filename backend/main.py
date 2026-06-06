from __future__ import annotations

import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = logging.getLogger(__name__)

from backend.agents.narrative import NarrativeAgent
from backend.config import settings
from backend.core.llm import LLMClient
from backend.core.memory import MemoryManager
from backend.core.preprocessor import detect_language, parse_chapters
from backend.schemas.models import (
    AlignmentResponse,
    ConvertResponse,
    DetectLanguageResponse,
    HealthResponse,
    ImportEditsResponse,
    NovelUploadRequest,
    TaskStatus,
    UploadResponse,
    UsageStats,
    ValidateResponse,
)
from backend.schemas.validator import _DEMO_SCREENPLAY_YAML, validate_screenplay_yaml
from backend.workflows.novel2screen import Novel2ScreenWorkflow

_task_store: dict[str, dict[str, Any]] = {}
_workflow: Novel2ScreenWorkflow | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Novel2Screen",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_workflow() -> Novel2ScreenWorkflow:
    global _workflow
    if _workflow is None:
        _workflow = Novel2ScreenWorkflow(settings, LLMClient(), MemoryManager())
    return _workflow


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse()

@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "Novel2Screen", "version": "2.0.0", "docs": "/docs", "frontend": "http://localhost:3000"}


@app.post("/novels/upload", response_model=UploadResponse)
async def upload_novel(file: UploadFile = File(...)) -> UploadResponse:
    content = await file.read()
    novel_text = content.decode("utf-8")
    task_id = f"task_{uuid.uuid4().hex[:12]}"
    language = detect_language(novel_text)
    chapters = parse_chapters(novel_text)
    chapter_count = len(chapters)
    _task_store[task_id] = {
        "status": "uploaded",
        "progress": 0.0,
        "current_stage": "File uploaded",
        "output": "",
        "novel_text": novel_text,
        "filename": file.filename or "unknown",
        "language": language,
    }
    return UploadResponse(
        task_id=task_id,
        filename=file.filename or "unknown",
        char_count=len(novel_text),
        language=language,
        chapter_count=chapter_count,
    )


@app.post("/generate/{task_id}", response_model=ConvertResponse)
async def generate_screenplay(
    task_id: str,
    mode: str = Query("auto"),
    pipeline: str = Query("full"),
) -> ConvertResponse:
    if task_id not in _task_store:
        raise HTTPException(status_code=404, detail="Task not found")

    task_data = _task_store[task_id]
    novel_text = task_data.get("novel_text", "")
    if not novel_text:
        raise HTTPException(status_code=400, detail="No novel text found in task")

    _task_store[task_id]["status"] = "processing"
    _task_store[task_id]["progress"] = 10.0
    _task_store[task_id]["current_stage"] = "正在分析..."

    asyncio.create_task(_run_generation(task_id, novel_text, mode, pipeline))
    return ConvertResponse(task_id=task_id, status="generating")


@app.get("/tasks/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str) -> TaskStatus:
    if task_id not in _task_store:
        raise HTTPException(status_code=404, detail="Task not found")

    td = _task_store[task_id]
    return TaskStatus(
        task_id=task_id,
        status=td.get("status", "unknown"),
        progress=td.get("progress", 0.0),
        current_stage=td.get("current_stage", ""),
        output=td.get("output", ""),
        error=td.get("error", ""),
    )


@app.get("/export/yaml/{task_id}")
async def export_yaml(task_id: str) -> dict[str, Any]:
    if task_id not in _task_store:
        raise HTTPException(status_code=404, detail="Task not found")

    td = _task_store[task_id]
    yaml_content = td.get("yaml_content") or td.get("output", "")

    if not yaml_content:
        raise HTTPException(status_code=400, detail="No YAML content generated yet")

    wf = _get_workflow()
    wf.save_export(task_id, yaml_content)

    return {"task_id": task_id, "yaml_content": yaml_content, "filename": f"{task_id}.yaml"}


@app.post("/import-edits/{task_id}", response_model=ImportEditsResponse)
async def import_edits(task_id: str, body: dict[str, Any]) -> ImportEditsResponse:
    if task_id not in _task_store:
        raise HTTPException(status_code=404, detail="Task not found")

    edited_yaml = body.get("yaml_content", "")
    if not edited_yaml:
        raise HTTPException(status_code=400, detail="No yaml_content provided")

    wf = _get_workflow()
    result = wf.import_edits(task_id, edited_yaml)

    if result.get("repaired_yaml"):
        _task_store[task_id]["yaml_content"] = result["repaired_yaml"]

    return ImportEditsResponse(
        task_id=task_id,
        status=result.get("status", "validated"),
        validated=result.get("validated", False),
        repaired_yaml=result.get("repaired_yaml", ""),
        changes=result.get("changes", []),
    )


@app.get("/alignment/{task_id}", response_model=AlignmentResponse)
async def get_alignment(task_id: str) -> AlignmentResponse:
    if task_id not in _task_store:
        raise HTTPException(status_code=404, detail="Task not found")

    td = _task_store[task_id]
    wf = _get_workflow()
    chapters = wf.parse_and_segment(td.get("novel_text", ""))

    alignment = [
        {
            "chapter_index": ch.get("index", i),
            "chapter_title": ch.get("title", ""),
            "episode_mapping": f"ep_{(i // 2 + 1):03d}",
            "key_passages": [p[:100] for p in ch.get("content", "").split("\n\n")[:3]],
        }
        for i, ch in enumerate(chapters)
    ]

    return AlignmentResponse(
        task_id=task_id,
        original_text_alignment=alignment,
        scene_to_source=[],
    )


class ConvertRequest(BaseModel):
    novel_text: str
    pipeline: str = "fast"
    language: str = "auto"
    model_config = {"extra": "ignore"}


class ValidateRequest(BaseModel):
    yaml_content: str


@app.post("/convert", response_model=ConvertResponse)
async def convert_novel(request: Request, pipeline: str = Query(None)) -> ConvertResponse:
    raw_body = await request.body()
    logger.info(f"[/convert] raw body ({len(raw_body)} bytes): {raw_body[:500]}")
    try:
        data = json.loads(raw_body)
    except json.JSONDecodeError as e:
        logger.error(f"[/convert] JSON parse failed: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
    logger.info(f"[/convert] parsed keys: {list(data.keys())}")

    novel_text = data.get("novel_text", "")
    if not novel_text:
        raise HTTPException(status_code=400, detail="novel_text is required")

    if pipeline is None:
        pipeline = data.get("pipeline", "fast" if len(novel_text) < 15000 else "full")

    task_id = f"task_{uuid.uuid4().hex[:12]}"
    _task_store[task_id] = {
        "status": "processing",
        "progress": 0.0,
        "current_stage": "Starting conversion...",
        "output": "",
        "novel_text": novel_text,
    }

    if pipeline == "demo":
        _task_store[task_id].update({
            "status": "completed",
            "progress": 100.0,
            "current_stage": "Demo complete",
            "output": _DEMO_SCREENPLAY_YAML,
            "yaml_content": _DEMO_SCREENPLAY_YAML,
        })
        return ConvertResponse(
            task_id=task_id,
            status="completed",
            message="Demo screenplay generated",
            yaml_content=_DEMO_SCREENPLAY_YAML,
        )

    asyncio.create_task(_run_generation(task_id, novel_text, "auto", pipeline))
    return ConvertResponse(task_id=task_id, status="generating")


class FileConvertRequest(BaseModel):
    content: str
    filename: str = ""
    mode: str = "auto"
    pipeline: str = "full"


@app.post("/convert/file", response_model=ConvertResponse)
async def convert_novel_file(request: FileConvertRequest) -> ConvertResponse:
    task_id = f"task_{uuid.uuid4().hex[:12]}"
    _task_store[task_id] = {
        "status": "processing",
        "progress": 0.0,
        "current_stage": "Starting file conversion...",
        "output": "",
        "novel_text": request.content,
        "filename": request.filename,
    }

    wf = _get_workflow()
    loop = asyncio.get_event_loop()

    result = await loop.run_in_executor(
        None,
        lambda: wf.fast_run(request.content, request.mode)
        if request.pipeline == "fast"
        else wf.run(request.content, request.mode),
    )

    status = result.get("status", "completed")
    yaml_content = result.get("yaml_content", "")
    _task_store[task_id].update({
        "status": status,
        "progress": 100.0,
        "current_stage": "Complete",
        "output": yaml_content,
        "yaml_content": yaml_content,
    })

    return ConvertResponse(task_id=task_id, status=status, yaml_content=yaml_content)


@app.post("/validate", response_model=ValidateResponse)
async def validate_yaml(body: dict[str, Any]) -> ValidateResponse:
    yaml_content = body.get("yaml_content", "")
    if not yaml_content:
        raise HTTPException(status_code=400, detail="No yaml_content provided")

    report = validate_screenplay_yaml(yaml_content)
    return ValidateResponse(
        valid=report.valid,
        errors=report.errors,
        warnings=report.warnings,
    )


@app.get("/usage", response_model=UsageStats)
async def get_usage() -> UsageStats:
    return UsageStats(
        total_llm_calls=len(_task_store),
        total_tokens=0,
        total_cost_estimate=0.0,
    )


@app.post("/detect-language", response_model=DetectLanguageResponse)
async def detect_novel_language(body: dict[str, Any]) -> DetectLanguageResponse:
    text = body.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="No text provided")
    lang = detect_language(text)
    return DetectLanguageResponse(language=lang, confidence=0.95)


async def _run_generation(task_id: str, novel_text: str, mode: str, pipeline: str) -> None:
    """Background generation task with progress tracking."""
    wf = _get_workflow()
    stages = [(15, "Analyzing narrative..."), (40, "Extracting characters..."), (70, "Building screenplay..."), (90, "Generating YAML...")] if pipeline == "fast" else [(10, "Analyzing narrative..."), (20, "Extracting characters..."), (30, "Analyzing world..."), (40, "Organizing timeline..."), (50, "Planning episodes..."), (60, "Planning scenes..."), (70, "Writing dialogue..."), (80, "Quality review..."), (90, "Generating YAML...")]
    for pg, st in stages:
        if task_id in _task_store:
            _task_store[task_id]["progress"] = float(pg)
            _task_store[task_id]["current_stage"] = st
    try:
        result = await asyncio.to_thread(wf.fast_run if pipeline == "fast" else wf.run, novel_text, mode)
        status = result.get("status", "completed")
        yaml_content = result.get("yaml_content", "")
        if task_id in _task_store:
            _task_store[task_id].update({"status": status, "progress": 100.0, "current_stage": "Complete" if status == "completed" else "Failed", "output": yaml_content, "yaml_content": yaml_content})
    except Exception as e:
        logger.exception("_run_generation failed")
        if task_id in _task_store:
            _task_store[task_id].update({"status": "failed", "progress": 100.0, "current_stage": "Error", "error": str(e)})
