"""
Novel2Screen - FastAPI Backend Server
Multi-Agent System for Novel-to-Screenplay Conversion
"""
import os
import json
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
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
        
        return ConvertResponse(
            task_id="task_001",
            status="completed" if state["completed"] else "partial",
            screenplay_yaml=state.get("screenplay_yaml", ""),
            violations=state.get("violations", []),
            critic_score=state.get("critic_score", 1.0),
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

if __name__ == "__main__":
    import uvicorn
    # Run directly when started from project root
    uvicorn.run(
        "backend.main:app",
        host=HOST,
        port=PORT,
        reload=True,
        reload_dirs=[os.path.dirname(os.path.dirname(__file__))]
    )
