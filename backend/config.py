from __future__ import annotations

from typing import Any

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""
    DATABASE_URL: str = "sqlite:///./data/novel2screen.db"
    QDRANT_URL: str = ""
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    MODE_DEFAULT: str = "long"
    EMBEDDING_MODEL: str = "BAAI/bge-small-zh-v1.5"
    CHUNK_SIZE: int = 1500
    CHUNK_OVERLAP: int = 200
    MAX_INPUT_CHARS: int = 50000
    DEEPSEEK_MAX_TOKENS: int = 4096
    RATE_LIMIT: str = "10/minute"
    CORS_ORIGINS: list[str] = ["*"]
    API_SECRET_KEY: str = "change-me-in-production"
    model_config: dict[str, Any] = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
