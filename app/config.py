from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# LangGraph/LangSmith read tracing configuration from the process environment.
# Load .env before importing modules that construct the graph or tracing client.
load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://po_agent:po_agent@localhost:5432/po_agent"
    attachment_dir: Path = Path("data/attachments")
    max_attachment_bytes: int = Field(default=10 * 1024 * 1024, gt=0)
    auto_create_schema: bool = True
    extraction_backend: Literal["openai", "development"] = "openai"
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-5.4-mini"
    openai_timeout_seconds: float = Field(default=90, gt=0)
    min_extraction_confidence: float = Field(default=0.85, ge=0, le=1)
    max_document_characters: int = Field(default=150_000, gt=0)
    log_level: str = "INFO"
    langsmith_tracing: bool = False
    langsmith_project: str = "po-intake-agent"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = Field(default=1536, gt=0)
    rag_top_k: int = Field(default=4, gt=0, le=20)
    rag_match_threshold: float = Field(default=0.70, ge=0, le=1)
    price_tolerance_percent: float = Field(default=1.0, ge=0, le=100)
    gmail_enabled: bool = False
    gmail_credentials_path: Path = Path("secrets/gmail-credentials.json")
    gmail_token_path: Path = Path("secrets/gmail-token.json")
    gmail_poll_interval_seconds: int = Field(default=30, ge=10)
    gmail_query: str = "is:unread has:attachment newer_than:7d"
    gmail_max_messages_per_poll: int = Field(default=25, ge=1, le=100)


@lru_cache
def get_settings() -> Settings:
    return Settings()
