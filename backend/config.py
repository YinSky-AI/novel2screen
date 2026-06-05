# Novel2Screen Backend Configuration
import os
from typing import Literal

# Mode
MODE_DEFAULT: Literal["short", "long"] = os.getenv("MODE_DEFAULT", "short")

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
# DeepSeek (OpenAI-compatible)
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
# DeepSeek extended config
DEEPSEEK_MAX_TOKENS = int(os.getenv("DEEPSEEK_MAX_TOKENS", "16384"))
DEEPSEEK_CONTEXT_WINDOW = 128000
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")
MAX_INPUT_CHARS = int(os.getenv("MAX_INPUT_CHARS", "120000"))




# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./novel2screen.db")

# Vector DB (ChromaDB - embedded, no external service required)
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
CHUNK_SIZE = 1500
CHUNK_OVERLAP = 200
TOP_K_LONG = 5
TOP_K_SHORT = 3
RAG_ENABLED = os.getenv("RAG_ENABLED", "true").lower() == "true"

# CORS
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000,http://127.0.0.1:8000",
).split(",")

# Task limits
MAX_RETRIES = 2
SHORT_MODE_CHAPTER_LIMIT = 10
LONG_MODE_CHAPTER_LIMIT = 100

# Server
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
