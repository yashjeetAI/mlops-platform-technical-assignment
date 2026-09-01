"""FastAPI application entrypoint."""
from fastapi import FastAPI

from app.api.routes import health
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="MLOps control plane: registry, deployments, monitoring.",
)

app.include_router(health.router)


@app.get("/", tags=["root"])
def root() -> dict[str, str]:
    return {"service": settings.app_name, "docs": "/docs"}
