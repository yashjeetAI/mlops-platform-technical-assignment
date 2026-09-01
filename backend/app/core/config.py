"""Application configuration loaded from environment variables."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "MLOps Platform"
    environment: str = "local"
    # Default to SQLite for zero-config local runs; override with Postgres in Docker.
    database_url: str = "sqlite:///./mlops.db"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
