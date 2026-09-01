"""Programmatic Alembic runner used at application startup."""
from pathlib import Path

from alembic import command
from alembic.config import Config

# backend/ (contains alembic.ini and the alembic/ directory)
BACKEND_DIR = Path(__file__).resolve().parents[2]


def _alembic_config() -> Config:
    return Config(str(BACKEND_DIR / "alembic.ini"))


def upgrade_to_head() -> None:
    """Apply all pending migrations. env.py supplies the DB URL from settings."""
    command.upgrade(_alembic_config(), "head")
