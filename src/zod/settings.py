from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://zod:zod@localhost:5432/zod"
    # Comma-separated list of web origins allowed to call the API from a browser.
    cors_origins: str = "http://localhost:3100"

    @field_validator("database_url")
    @classmethod
    def use_psycopg3(cls, v: str) -> str:
        # Hosts hand out "postgres://" or "postgresql://" URLs; SQLAlchemy needs the driver named.
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v[len(prefix) :]
        return v


@lru_cache
def settings() -> Settings:
    return Settings()
