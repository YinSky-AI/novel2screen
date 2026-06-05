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
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")


# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./novel2screen.db")

# Vector DB
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
EMBEDDING_MODEL = "BAAI/bge-large-en-v1.5"
CHUNK_SIZE = 1500
CHUNK_OVERLAP = 200
TOP_K_LONG = 5
TOP_K_SHORT = 3

# Task limits
MAX_RETRIES = 2
SHORT_MODE_CHAPTER_LIMIT = 10
LONG_MODE_CHAPTER_LIMIT = 100

# Server
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
