"""Model registry request/response schemas (camelCase JSON via CamelModel)."""
from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.core.enums import Framework, LifecycleStage
from app.schemas.base import CamelModel

# --- requests ---

class ModelCreate(CamelModel):
    # `key` (slug) is derived from `name` by the backend, not supplied by the client.
    name: str = Field(min_length=1, max_length=255)
    owner: str = Field(min_length=1, max_length=255)
    framework: Framework
    tags: dict = Field(default_factory=dict)


class ModelVersionCreate(CamelModel):
    version: str = Field(min_length=1, max_length=64)
    artifact_uri: str = Field(min_length=1, max_length=512)
    algorithm: str | None = Field(default=None, max_length=128)
    training_data_ref: str | None = Field(default=None, max_length=512)
    tags: dict = Field(default_factory=dict)


class StageChangeRequest(CamelModel):
    target_stage: LifecycleStage


# --- responses ---

class ModelVersionResponse(CamelModel):
    id: UUID
    model_id: UUID
    version: str
    stage: LifecycleStage
    approved: bool
    algorithm: str | None
    artifact_uri: str
    training_data_ref: str | None
    tags: dict
    approved_by: UUID | None
    approved_at: datetime | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime


class ModelResponse(CamelModel):
    id: UUID
    key: str
    name: str
    owner: str
    framework: str
    tags: dict
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime


class ModelPage(CamelModel):
    items: list[ModelResponse]
    total: int
    limit: int
    offset: int


class ModelVersionPage(CamelModel):
    items: list[ModelVersionResponse]
    total: int
    limit: int
    offset: int


class ModelVersionEventResponse(CamelModel):
    id: UUID
    event: str
    from_stage: LifecycleStage | None
    to_stage: LifecycleStage
    actor: str | None
    correlation_id: str | None
    created_at: datetime


class ModelVersionEventPage(CamelModel):
    items: list[ModelVersionEventResponse]
    total: int
    limit: int
    offset: int
