"""Deployment request/response schemas (camelCase JSON via CamelModel)."""
from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.core.enums import DeploymentStatus, Environment
from app.schemas.base import CamelModel


class DeploymentCreate(CamelModel):
    model_version_id: UUID
    environment: Environment
    # Optional client-supplied key to make duplicate requests idempotent.
    idempotency_key: str | None = Field(default=None, max_length=128)
    # Demo/test hook to force the worker to fail this deployment.
    simulate_failure: bool = False


class DeploymentEventResponse(CamelModel):
    id: UUID
    status: DeploymentStatus
    event: str
    message: str | None
    actor: str | None
    correlation_id: str | None
    created_at: datetime


class DeploymentResponse(CamelModel):
    id: UUID
    model_id: UUID
    model_version_id: UUID
    environment: Environment
    status: DeploymentStatus
    idempotency_key: str | None
    attempts: int
    error: str | None
    correlation_id: str | None
    rolled_back_to_id: UUID | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime


class DeploymentDetailResponse(DeploymentResponse):
    events: list[DeploymentEventResponse] = Field(default_factory=list)
