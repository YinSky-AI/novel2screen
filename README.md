# Novel2Screen

> Multi-Agent System for Novel-to-Screenplay Conversion
> 将小说自动改编为结构化剧本，支持 DeepSeek / OpenAI / Anthropic

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-green)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## Features

- **Multi-Agent** -- 9 specialized agents (Narrative, Character, World, Timeline, Episode/Scene Planning, Dialogue, Critic, Repair, Consistency)
- **Dual Pipeline** -- `fast` (2-3 LLM calls, ~15s) or `full` (9+ agent chain, maximum quality)
- **RAG with ChromaDB** -- embedded vector search for long novels, no external service required
- **Demo Mode** -- instantly generate sample screenplay without any API key
- **Multi-Provider** -- DeepSeek / OpenAI / Anthropic / Ollama auto-fallback chain
- **Web UI** -- single-page layout with light/dark themes, file upload, one-click export

---

## Quick Start

### Prerequisites

- Python 3.11+
- DeepSeek API Key (recommended), or OpenAI / Anthropic key

### Install & Run

```bash
git clone https://github.com/YinSky-AI/novel2screen.git
cd novel2screen

python -m venv venv
venv\Scripts\activate     # Windows
# source venv/bin/activate  # macOS/Linux

pip install -r backend/requirements.txt

# Set API key
set DEEPSEEK_API_KEY=sk-your-key-here   # Windows
# export DEEPSEEK_API_KEY=sk-your-key-here  # macOS/Linux

# Start server
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Open **http://localhost:8000** in your browser.

---

## Architecture

```
Novel Input
    │
    ▼
┌─────────────────┐
│  Parser          │  Auto-detect chapter boundaries
└────────┬────────┘
         ▼
┌─────────────────┐
│  Preprocess      │  1 LLM call → narrative + characters + world + locations
│  (with RAG)      │  ChromaDB retrieval injects relevant context for long novels
└────────┬────────┘
         ▼
┌─────────────────┐
│  Batch Plan      │  1 LLM call → all episodes + scenes + beats + dialogue
│  (with RAG)      │
└────────┬────────┘
         ▼
┌─────────────────┐
│  Critic + Repair │  1 LLM call → quality score + auto-fix
└────────┬────────┘
         ▼
    📄 YAML Screenplay
```

### Pipeline Modes

| Mode | LLM Calls | Time | Quality | Use Case |
|------|-----------|------|---------|----------|
| Demo | 0 | <1s | Sample | Instant preview |
| Fast | 2-3 | 15-30s | Good | Production default |
| Full | 9+ | 60-120s | Maximum | Long novels (>10 ch) |

### RAG Flow

- Novels >5000 chars trigger RAG injection
- ChromaDB (embedded, SQLite-backed) replaces Qdrant -- **zero external dependencies**
- Top-K retrieval: 3 (short mode) / 5 (long mode)
- Fallback: keyword matching if ChromaDB unavailable

---

## Project Structure

```
novel2screen/
├── backend/
│   ├── agents/              # 9 AI Agent modules + base class
│   │   ├── narrative.py       # Narrative structure extraction
│   │   ├── character.py       # Character profile extraction
│   │   ├── world.py           # World-building (long mode)
│   │   ├── timeline.py        # Timeline organization
│   │   ├── episode_planner.py # Episode structure planning
│   │   ├── scene_planner.py   # Scene-by-scene planning
│   │   ├── dialogue.py        # Dialogue + beat writing
│   │   ├── critic.py          # Quality review
│   │   ├── repair.py          # Auto-fix violations
│   │   ├── consistency.py     # Novel-to-screenplay alignment
│   │   └── base.py            # Agent ABC (run/validate/retry)
│   ├── core/                # LLM client, memory (ChromaDB RAG), prompts
│   ├── schemas/             # Pydantic models & YAML validation
│   ├── workflows/           # Pipeline orchestrator (fast + full)
│   ├── config.py            # Configuration & model selection
│   └── main.py              # FastAPI server
├── frontend/                # Single-page web UI
├── tests/                   # unit + integration tests
├── mcp-server/              # MCP protocol server
├── data/                    # sample data & exports
└── docs/                    # design documents
```

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Web UI |
| `POST` | `/convert` | Convert text to screenplay |
| `POST` | `/convert/file` | Upload file for conversion |
| `POST` | `/validate` | Validate YAML against schema |
| `GET` | `/export/{title}` | Download screenplay YAML |
| `GET` | `/docs` | Swagger API docs |
| `POST` | `/novels/upload` | Upload novel, get task_id |
| `POST` | `/generate/{task_id}` | Generate from uploaded novel |
| `GET` | `/tasks/{task_id}` | Get task status |
| `POST` | `/import-edits/{task_id}` | Import edited YAML + reconcile |
| `GET` | `/alignment/{task_id}` | Get consistency report |
| `GET` | `/usage` | LLM usage & cost stats |
| `GET` | `/health` | Health check |

### Examples

```bash
# Convert (fast mode, with API key)
curl -X POST http://localhost:8000/convert \
  -H "Content-Type: application/json" \
  -d '{"novel_text": "第一章...\n\n第二章...\n\n第三章...", "title": "My Novel", "pipeline": "fast"}'

# Convert (full agent chain)
curl -X POST http://localhost:8000/convert \
  -H "Content-Type: application/json" \
  -d '{"novel_text": "...", "title": "My Novel", "pipeline": "full"}'

# Demo mode (no API key needed)
curl -X POST http://localhost:8000/convert \
  -H "Content-Type: application/json" \
  -d '{"novel_text": "any placeholder text...", "demo": true}'

# Validate YAML
curl -X POST http://localhost:8000/validate \
  -F 'yaml_text=@output.yaml'

# Import human edits
curl -X POST http://localhost:8000/import-edits/task_000001 \
  -H "Content-Type: application/json" \
  -d '{"edited_yaml": "..."}'
```

---

## Configuration

Environment variables (see `backend/config.py`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DEEPSEEK_API_KEY` | - | DeepSeek API key |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | API base URL |
| `DEEPSEEK_MODEL` | `deepseek-v4-flash` | Model name |
| `OPENAI_API_KEY` | - | OpenAI fallback |
| `ANTHROPIC_API_KEY` | - | Anthropic fallback |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Local Ollama |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Ollama model |
| `RAG_ENABLED` | `true` | Enable/disable RAG |
| `CHROMA_PERSIST_DIR` | `./data/chroma_db` | ChromaDB storage |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformers model |
| `DATABASE_URL` | `sqlite:///./novel2screen.db` | SQLAlchemy DB URL |
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8000` | Server port |

---

## Human-in-the-Loop Workflow

1. Generate screenplay via `/convert` or `/generate/{task_id}`
2. Download YAML via `/export/yaml/{task_id}`
3. Edit YAML externally (add/remove/modify scenes, beats, characters)
4. Re-upload via `/import-edits/{task_id}` -- system:
   - Validates YAML against schema (422 on failure)
   - Runs RepairAgent on changed parts
   - Produces BidirectionalConsistencyAgent alignment report
   - Returns reconciled YAML

---

## Testing

```bash
cd backend
pip install pytest chromadb sentence-transformers

# Run unit tests
python -m pytest tests/unit/ -v

# Run integration tests
python -m pytest tests/integration/ -v

# Run all
python -m pytest tests/ -v
```

---

## Tech Stack

- **Backend**: FastAPI + Pydantic + PyYAML + SQLAlchemy
- **AI**: DeepSeek V4 Flash (default) / OpenAI / Anthropic / Ollama
- **RAG**: ChromaDB (embedded vector DB) + sentence-transformers
- **Frontend**: Vanilla HTML/CSS/JS (zero framework)
- **Workflow**: LangGraph-style state machine

---

## License

MIT (c) YinSky-AI
