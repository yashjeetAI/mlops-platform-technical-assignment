"""Application configuration loaded from environment variables."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "MLOps Platform"
    environment: str = "local"
    # Postgres is the single source of truth for the app (matches Docker Compose).
    # Tests override this with in-memory SQLite via dependency injection.
    database_url: str = "postgresql+psycopg://mlops:mlops@localhost:5432/mlops"
    log_level: str = "INFO"

    # Auth / JWT. Override jwt_secret via env in any real deployment.
    jwt_secret: str = "dev-insecure-change-me-please-32byte-minimum-secret"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 480
    # Password for all seeded demo users (demo convenience only).
    demo_password: str = "demo1234"
    # Directory holding sample seed data (models.json, metrics.csv). In Docker
    # the repo-root data/ folder is mounted and this is set via SEED_DATA_DIR;
    # locally it defaults to the repo-root data/ directory.
    seed_data_dir: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
