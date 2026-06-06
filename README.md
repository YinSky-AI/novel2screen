# Novel2Screen

AI-powered multi-agent system for novel-to-screenplay conversion.

## Setup
```bash
pip install -r requirements.txt
cp .env.example .env  # Edit with your API keys
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
