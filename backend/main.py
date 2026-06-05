"""
Novel2Screen - FastAPI Backend Server
Multi-Agent System for Novel-to-Screenplay Conversion
"""
import os
import json
from fastapi import Body,  FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel

from .workflows.novel2screen import Novel2ScreenWorkflow, route_mode
from .schemas.validator import validate_screenplay_yaml, screenplay_to_yaml, yaml_to_screenplay
from .config import HOST, PORT

from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(
    title="Novel2Screen API",
    description="Multi-Agent System for Novel-to-Screenplay Conversion",
    version="2.0.0",
)

# Serve frontend static files
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=os.path.join(FRONTEND_DIR, "src")), name="static")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory workflow instances (in production, use a task queue)
workflow = Novel2ScreenWorkflow()


# ── Request/Response Models ──

class ConvertRequest(BaseModel):
    novel_text: str
    title: str = "Untitled"
    genre: str = "Drama"
    mode: str = ""
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


# ── Routes ──

@app.get("/")
async def root():
    from fastapi.responses import FileResponse
    frontend_index = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "index.html")
    if os.path.isfile(frontend_index):
        return FileResponse(frontend_index)
    return {"service": "Novel2Screen",
        "version": "2.0.0",
        "endpoints": {
            "POST /convert": "Convert novel text to screenplay",
            "POST /convert/file": "Upload novel file for conversion",
            "GET /export/{title}": "Download screenplay YAML",
            "POST /validate": "Validate screenplay YAML",
        },
    }


@app.post("/convert", response_model=ConvertResponse)
async def convert_novel(req: ConvertRequest):
    """Convert novel text to screenplay YAML."""
    if len(req.novel_text) < 100:
        raise HTTPException(status_code=400, detail="Novel text too short (minimum 100 characters)")
    
    # Demo mode: return sample data instantly
    if req.demo:
        from .schemas.validator import _DEMO_SCREENPLAY_YAML
        return ConvertResponse(
            task_id="task_demo",
            status="completed",
            screenplay_yaml=_DEMO_SCREENPLAY_YAML,
            violations=[],
            critic_score=0.92,
        )
    
    try:
        state = workflow.fast_run(
            novel_text=req.novel_text,
            novel_title=req.title,
            genre=req.genre,
            mode=req.mode,
        )
        
        if state.get("error"):
            return ConvertResponse(
                task_id="task_001",
                status="error",
                error=state["error"],
            )
        
        # Calculate stats from state
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
        )
    except Exception as e:
        return ConvertResponse(
            task_id="task_001",
            status="error",
            error=str(e),
        )


@app.post("/convert/file")
async def convert_novel_file(
    file: UploadFile = File(...),
    title: str = Form("Untitled"),
    genre: str = Form("Drama"),
    mode: str = Form(""),
):
    """Upload a novel file (.txt, .md) for conversion."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    content = await file.read()
    try:
        novel_text = content.decode("utf-8")
    except UnicodeDecodeError:
        novel_text = content.decode("gbk", errors="replace")
    
    if not title or title == "Untitled":
        title = os.path.splitext(file.filename)[0]
    
    state = workflow.fast_run(
        novel_text=novel_text,
        novel_title=title,
        genre=genre,
        mode=mode,
    )
    
    if state.get("error"):
        return {"status": "error", "error": state["error"]}
    
    return {
        "status": "completed",
        "title": title,
        "mode": state.get("mode", "short"),
        "chapters_processed": len(state.get("novel_chunks", [])),
        "characters_extracted": len(state.get("characters", {}).get("characters", [])),
        "episodes_planned": len(state.get("episode_plan", {}).get("episodes", [])),
        "scenes_written": len(state.get("dialogue_scenes", [])),
        "critic_score": state.get("critic_score", 1.0),
        "violations": len(state.get("violations", [])),
        "screenplay_yaml": state.get("screenplay_yaml", ""),
    }


@app.post("/validate")
async def validate_yaml(yaml_text: str = Form(...)):
    """Validate a screenplay YAML against the schema."""
    is_valid, errors = validate_screenplay_yaml(yaml_text)
    return {"valid": is_valid, "errors": errors}


@app.get("/export/{title:path}")
async def export_screenplay(title: str):
    """Download a screenplay YAML file."""
    export_dir = "data/exports"
    os.makedirs(export_dir, exist_ok=True)
    filepath = os.path.join(export_dir, f"{title}.screenplay.yaml")
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Screenplay not found")
    
    return FileResponse(
        filepath,
        media_type="text/yaml",
        filename=f"{title}.screenplay.yaml",
    )


# ── Entrypoint ──



@app.get("/usage")
async def get_usage():
    """Get LLM usage statistics and cost estimates."""
    try:
        from .core.router import ModelRouter
        router = ModelRouter()
        cost_est = router.get_cost_estimate()
    except Exception:
        cost_est = {"total_est_usd": 0.02}
    
    try:
        from .core.llm import llm_client
        usage = llm_client.get_usage_report()
    except Exception:
        usage = {"total_cost_usd": 0, "call_count": 0}
    
    return {"usage": usage, "estimate_per_run": cost_est}


# ── In-memory task store (replace with DB in production) ──
_task_store: dict = {}
_task_id_counter: int = 0


def _generate_task_id() -> str:
    global _task_id_counter
    _task_id_counter += 1
    return f"task_{_task_id_counter:06d}"


@app.post("/novels/upload")
async def upload_novel(file: UploadFile = File(...)):
    """Upload a novel file (TXT/Markdown) and return a task_id."""
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


@app.post("/generate/{task_id}")
async def generate_screenplay(task_id: str, req: GenerateRequest = Body(...)):
    """Generate screenplay from an uploaded novel."""
    if task_id not in _task_store:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    task = _task_store[task_id]
    task["status"] = "generating"

    try:
        state = workflow.fast_run(
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

        return {
            "task_id": task_id,
            "status": task["status"],
            "screenplay_yaml": task["screenplay_yaml"],
            "violations": task["violations"],
            "critic_score": task["critic_score"],
        }
    except Exception as e:
        task["status"] = "error"
        task["error"] = str(e)
        return {"status": "error", "error": str(e)}


@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get task status and partial YAML."""
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
    """Download screenplay YAML for a task."""
    if task_id not in _task_store:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    task = _task_store[task_id]
    yaml_content = task.get("screenplay_yaml", "")
    if not yaml_content:
        raise HTTPException(status_code=404, detail="No screenplay generated yet")
    return PlainTextResponse(
        content=yaml_content,
        media_type="text/yaml",
        headers={"Content-Disposition": f"attachment; filename={task['title']}.yaml"},
    )


class ImportEditsRequest(BaseModel):
    edited_yaml: str


@app.post("/import-edits/{task_id}")
async def import_edits(task_id: str, req: ImportEditsRequest):
    """Import edited YAML and run incremental repair on changed scenes."""
    if task_id not in _task_store:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    task = _task_store[task_id]
    original_yaml = task.get("screenplay_yaml", "")

    if not original_yaml:
        raise HTTPException(status_code=400, detail="No original screenplay to compare")

    # Run repair on the edited YAML
    from .core.llm import llm_client
    from .core.prompts import REPAIR_SYSTEM, REPAIR_USER
    import hashlib

    repair_prompt = REPAIR_USER.format(violations="Human edits applied - reconcile and validate", screenplay=req.edited_yaml)
    repaired_yaml = llm_client.complete(
        system_prompt=REPAIR_SYSTEM,
        user_prompt=repair_prompt,
        temperature=0.1,
    )

    # Store the edit
    original_hash = hashlib.sha256(original_yaml.encode()).hexdigest()

    # Try to store in DB if available
    try:
        from .core.database import SessionLocal, HumanEdit
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
        pass  # DB not available, skip persistence

    return {"status": "reconciled", "repaired_yaml": repaired_yaml}


@app.get("/alignment/{task_id}")
async def get_alignment(task_id: str):
    """Get alignment report (optional, requires BidirectionalConsistencyAgent)."""
    if task_id not in _task_store:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    # Stub - returns basic stats
    task = _task_store[task_id]
    return {
        "task_id": task_id,
        "alignment_score": task.get("critic_score", 0.0),
        "deviations": [],
        "suggestions": ["Enable BidirectionalConsistencyAgent for full alignment report"],
    }
