"""Novel2Screen - FastAPI Backend Server
Multi-Agent System for Novel-to-Screenplay Conversion.
"""
import os
import traceback
from typing import Annotated

from fastapi import Body, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import ALLOWED_ORIGINS
from .schemas.validator import validate_screenplay_yaml
from .workflows.novel2screen import Novel2ScreenWorkflow

# Rate limiting
_rate_limit_store: dict = {}
RATE_LIMIT_MAX = 30  # requests per window
RATE_LIMIT_WINDOW = 60  # seconds


def _check_rate_limit(client_ip: str) -> bool:
    """Check if client has exceeded rate limit. Returns True if allowed."""
    import time
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    timestamps = _rate_limit_store.get(client_ip, [])
    timestamps = [t for t in timestamps if t > window_start]
    if len(timestamps) >= RATE_LIMIT_MAX:
        return False
    timestamps.append(now)
    _rate_limit_store[client_ip] = timestamps
    return True

app = FastAPI(
    title="Novel2Screen API",
    description="Multi-Agent System for Novel-to-Screenplay Conversion",
    version="2.1.0",
)

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=os.path.join(FRONTEND_DIR, "src")), name="static")


@app.middleware("http")
async def rate_limit_middleware(request, call_next):
    """Apply rate limiting to API endpoints."""
    if request.url.path not in ("/health", "/", "/static"):
        client_ip = request.client.host if request.client else "unknown"
        if not _check_rate_limit(client_ip):
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
            )
    return await call_next(request)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

workflow = Novel2ScreenWorkflow()


class ConvertRequest(BaseModel):
    novel_text: str
    title: str = "Untitled"
    genre: str = "Drama"
    mode: str = ""
    pipeline: str = "fast"
    demo: bool = False


class ConvertResponse(BaseModel):
    task_id: str
    status: str
    screenplay_yaml: str = ""
    error: str = ""
    violations: list = []
    critic_score: float = 1.0
    chapters_processed: int = 0
    characters_extracted: int = 0
    episodes_planned: int = 0
    scenes_written: int = 0
    pipeline: str = "fast"


@app.get("/")
async def root():
    frontend_index = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "index.html")
    if os.path.isfile(frontend_index):
        return FileResponse(frontend_index)
    return {
        "service": "Novel2Screen",
        "version": "2.1.0",
        "endpoints": {
            "POST /convert": "Convert novel text to screenplay (supports pipeline=fast|full)",
            "POST /convert/file": "Upload novel file for conversion",
            "GET /export/{title}": "Download screenplay YAML",
            "POST /validate": "Validate screenplay YAML",
            "POST /novels/upload": "Upload novel, get task_id",
            "POST /generate/{task_id}": "Generate from uploaded novel",
            "GET /tasks/{task_id}": "Get task status",
            "POST /import-edits/{task_id}": "Import edited YAML",
            "GET /alignment/{task_id}": "Get consistency report",
        },
    }


@app.post("/convert", response_model=ConvertResponse)
async def convert_novel(req: ConvertRequest):
    if len(req.novel_text) < 100:
        raise HTTPException(status_code=400, detail="Novel text too short (minimum 100 characters)")

    if req.demo:
        from .schemas.validator import _DEMO_SCREENPLAY_YAML
        return ConvertResponse(
            task_id="task_demo", status="completed",
            screenplay_yaml=_DEMO_SCREENPLAY_YAML,
            violations=[], critic_score=0.92, pipeline="demo",
        )

    try:
        if req.pipeline == "full":
            state = workflow.run(
                novel_text=req.novel_text, novel_title=req.title,
                genre=req.genre, mode=req.mode,
            )
        else:
            state = workflow.fast_run(
                novel_text=req.novel_text, novel_title=req.title,
                genre=req.genre, mode=req.mode,
            )

        if state.get("error"):
            return ConvertResponse(
                task_id="task_001", status="error",
                error=state["error"], pipeline=req.pipeline,
            )

        screenplay_data = state.get("screenplay", {})
        episodes_list = screenplay_data.get("episodes", []) if isinstance(screenplay_data, dict) else []
        total_scenes = sum(len(ep.get("scenes", [])) for ep in episodes_list)

        return ConvertResponse(
            task_id="task_001",
            status="completed" if state["completed"] else "partial",
            screenplay_yaml=state.get("screenplay_yaml", ""),
            violations=state.get("violations", []),
            critic_score=state.get("critic_score", 1.0),
            chapters_processed=len(state.get("novel_chunks", [])),
            characters_extracted=len(state.get("characters", {}).get("characters", [])),
            episodes_planned=len(episodes_list),
            scenes_written=total_scenes,
            pipeline=req.pipeline,
        )
    except Exception as e:
        return ConvertResponse(
            task_id="task_001", status="error",
            error=f"{type(e).__name__}: {e}\n{traceback.format_exc()}",
            pipeline=req.pipeline,
        )


@app.post("/convert/file")
async def convert_novel_file(
    file: Annotated[UploadFile, File()],
    title: Annotated[str, Form()] = "Untitled",
    genre: Annotated[str, Form()] = "Drama",
    mode: Annotated[str, Form()] = "",
    pipeline: Annotated[str, Form()] = "fast",
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    content = await file.read()
    try:
        novel_text = content.decode("utf-8")
    except UnicodeDecodeError:
        novel_text = content.decode("gbk", errors="replace")

    if not title or title == "Untitled":
        title = os.path.splitext(file.filename)[0]

    fn = workflow.run if pipeline == "full" else workflow.fast_run

    state = fn(novel_text=novel_text, novel_title=title, genre=genre, mode=mode)

    if state.get("error"):
        return {"status": "error", "error": state["error"]}

    screenplay_data = state.get("screenplay", {})
    episodes_list = screenplay_data.get("episodes", []) if isinstance(screenplay_data, dict) else []
    total_scenes = sum(len(ep.get("scenes", [])) for ep in episodes_list)

    return {
        "status": "completed" if state["completed"] else "partial",
        "title": title,
        "mode": state.get("mode", "short"),
        "pipeline": pipeline,
        "chapters_processed": len(state.get("novel_chunks", [])),
        "characters_extracted": len(state.get("characters", {}).get("characters", [])),
        "episodes_planned": len(episodes_list),
        "scenes_written": total_scenes,
        "critic_score": state.get("critic_score", 1.0),
        "violations": len(state.get("violations", [])),
        "screenplay_yaml": state.get("screenplay_yaml", ""),
    }


@app.post("/validate")
async def validate_yaml(yaml_text: Annotated[str, Form()]):
    is_valid, errors = validate_screenplay_yaml(yaml_text)
    return {"valid": is_valid, "errors": errors}


@app.get("/export/{title:path}")
async def export_screenplay(title: str):
    export_dir = os.path.join(os.path.dirname(__file__), "..", "data", "exports")
    os.makedirs(export_dir, exist_ok=True)
    filepath = os.path.join(export_dir, f"{title}.screenplay.yaml")

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Screenplay not found")

    return FileResponse(filepath, media_type="text/yaml", filename=f"{title}.screenplay.yaml")


@app.get("/usage")
async def get_usage():
    try:
        from .core.llm import llm_client
        usage = llm_client.get_usage_report()
    except Exception:
        usage = {"total_cost_usd": 0, "call_count": 0}
    return {"usage": usage, "estimate_per_run": {"total_est_usd": 0.02}}


_task_store: dict = {}
_task_id_counter: int = 0


def _generate_task_id() -> str:
    global _task_id_counter
    _task_id_counter += 1
    return f"task_{_task_id_counter:06d}"


@app.post("/novels/upload")
async def upload_novel(file: Annotated[UploadFile, File()]):
    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("gbk", errors="replace")

    task_id = _generate_task_id()
    _task_store[task_id] = {
        "status": "uploaded",
        "title": os.path.splitext(file.filename or "untitled")[0],
        "raw_text": text,
        "genre": "Drama",
        "screenplay_yaml": "",
        "error": "",
    }
    return {"task_id": task_id, "status": "uploaded", "filename": file.filename}


class GenerateRequest(BaseModel):
    mode: str = ""
    pipeline: str = "fast"


@app.post("/generate/{task_id}")
async def generate_screenplay(task_id: str, req: Annotated[GenerateRequest, Body()]):
    if task_id not in _task_store:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    task = _task_store[task_id]
    task["status"] = "generating"

    fn = workflow.run if req.pipeline == "full" else workflow.fast_run

    try:
        state = fn(
            novel_text=task["raw_text"],
            novel_title=task["title"],
            genre=task.get("genre", "Drama"),
            mode=req.mode or "",
        )

        if state.get("error"):
            task["status"] = "error"
            task["error"] = state["error"]
            return {"status": "error", "error": state["error"]}

        task["status"] = "completed" if state["completed"] else "partial"
        task["screenplay_yaml"] = state.get("screenplay_yaml", "")
        task["violations"] = state.get("violations", [])
        task["critic_score"] = state.get("critic_score", 1.0)
        task["novel_chunks"] = state.get("novel_chunks", [])

        return {
            "task_id": task_id,
            "status": task["status"],
            "screenplay_yaml": task["screenplay_yaml"],
            "violations": task["violations"],
            "critic_score": task["critic_score"],
            "pipeline": req.pipeline,
        }
    except Exception as e:
        task["status"] = "error"
        task["error"] = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        return {"status": "error", "error": task["error"]}


@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    if task_id not in _task_store:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    task = _task_store[task_id]
    return {
        "task_id": task_id,
        "status": task.get("status", "unknown"),
        "title": task.get("title", ""),
        "screenplay_yaml": task.get("screenplay_yaml", ""),
        "violations": task.get("violations", []),
        "critic_score": task.get("critic_score", None),
        "error": task.get("error", ""),
    }


@app.get("/export/yaml/{task_id}")
async def export_yaml(task_id: str):
    if task_id not in _task_store:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    task = _task_store[task_id]
    yaml_content = task.get("screenplay_yaml", "")
    if not yaml_content:
        raise HTTPException(status_code=400, detail="No screenplay generated yet")
    return PlainTextResponse(
        content=yaml_content,
        media_type="text/yaml",
        headers={"Content-Disposition": f"attachment; filename={task['title']}.yaml"},
    )


class ImportEditsRequest(BaseModel):
    edited_yaml: str


@app.post("/import-edits/{task_id}")
async def import_edits(task_id: str, req: ImportEditsRequest):
    if task_id not in _task_store:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    task = _task_store[task_id]
    original_yaml = task.get("screenplay_yaml", "")

    if not original_yaml:
        raise HTTPException(status_code=400, detail="No original screenplay to compare")

    import hashlib

    from .core.llm import llm_client
    from .core.prompts import REPAIR_SYSTEM, REPAIR_USER

    is_valid, errors = validate_screenplay_yaml(req.edited_yaml)
    if not is_valid:
        raise HTTPException(status_code=422, detail=f"Edited YAML validation failed: {errors}")

    repair_prompt = REPAIR_USER.format(
        violations="Human edits applied - reconcile and validate",
        screenplay=req.edited_yaml,
    )
    repaired_yaml = llm_client.complete(
        system_prompt=REPAIR_SYSTEM,
        user_prompt=repair_prompt,
        temperature=0.1,
    )

    consistency_report = workflow.run_consistency_check(
        novel_chunks=task.get("novel_chunks", []),
        screenplay_yaml=repaired_yaml or req.edited_yaml,
        human_edits=req.edited_yaml,
    )

    original_hash = hashlib.sha256(original_yaml.encode()).hexdigest()
    try:
        from .core.database import HumanEdit, SessionLocal
        db = SessionLocal()
        edit_record = HumanEdit(
            task_id=task_id,
            original_yaml_hash=original_hash,
            edited_yaml=req.edited_yaml,
            reconcile_status="accepted",
        )
        db.add(edit_record)
        db.commit()
        db.close()
    except Exception:
        pass

    task["repaired_yaml"] = repaired_yaml
    task["consistency"] = consistency_report

    return {
        "status": "reconciled",
        "repaired_yaml": repaired_yaml,
        "consistency": consistency_report,
    }


@app.get("/alignment/{task_id}")
async def get_alignment(task_id: str):
    if task_id not in _task_store:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    task = _task_store[task_id]

    novel_chunks = task.get("novel_chunks", [])
    screenplay_yaml = task.get("screenplay_yaml", "")

    if not screenplay_yaml:
        return {
            "task_id": task_id,
            "alignment_score": 0.0,
            "deviations": [],
            "suggestions": ["No screenplay generated yet"],
        }

    report = workflow.run_consistency_check(
        novel_chunks=novel_chunks,
        screenplay_yaml=screenplay_yaml,
    )
    return {
        "task_id": task_id,
        "alignment_score": report.get("alignment_score", 0.0),
        "deviations": report.get("deviations", []),
        "suggestions": report.get("suggestions", []),
    }


@app.get("/health")
async def health():
    from .config import CHROMA_PERSIST_DIR, RAG_ENABLED
    return {
        "status": "ok",
        "version": "2.1.0",
        "rag_enabled": RAG_ENABLED,
        "chroma_dir": CHROMA_PERSIST_DIR,
    }


@app.on_event("shutdown")
async def shutdown():
    _task_store.clear()
