"""FastAPI application entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import auth, health, models
from app.core.config import get_settings
from app.core.exceptions import (
    ApprovalRequired,
    ConflictError,
    DomainError,
    InvalidStateTransition,
    NotFoundError,
)
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
app.include_router(models.router)


# Map domain errors to consistent HTTP responses (keeps services HTTP-agnostic).
_DOMAIN_ERROR_STATUS: dict[type[DomainError], int] = {
    NotFoundError: 404,
    ConflictError: 409,
    InvalidStateTransition: 409,
    ApprovalRequired: 409,
}


@app.exception_handler(DomainError)
async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
    status_code = next(
        (code for klass, code in _DOMAIN_ERROR_STATUS.items() if isinstance(exc, klass)),
        400,
    )
    return JSONResponse(status_code=status_code, content={"detail": exc.message})


@app.get("/", tags=["root"])
def root() -> dict[str, str]:
    return {"service": settings.app_name, "docs": "/docs"}
