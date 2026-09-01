"""FastAPI application entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import auth, health
from app.core.config import get_settings
from app.db.migrations import upgrade_to_head
from app.db.seed import seed_demo_users
from app.db.session import SessionLocal

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Schema is managed by Alembic migrations (Postgres). Tests bypass this and
    # build the schema directly on SQLite via fixtures.
    upgrade_to_head()
    with SessionLocal() as db:
        seed_demo_users(db)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="MLOps control plane: registry, deployments, monitoring.",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(auth.router)


@app.get("/", tags=["root"])
def root() -> dict[str, str]:
    return {"service": settings.app_name, "docs": "/docs"}
