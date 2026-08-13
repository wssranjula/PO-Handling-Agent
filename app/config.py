from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://po_agent:po_agent@localhost:5432/po_agent"
    attachment_dir: Path = Path("data/attachments")
    max_attachment_bytes: int = Field(default=10 * 1024 * 1024, gt=0)
    auto_create_schema: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
