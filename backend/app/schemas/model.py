"""Model registry request/response schemas (camelCase JSON via CamelModel)."""
from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.core.enums import LifecycleStage
from app.schemas.base import CamelModel


# --- requests ---

class ModelCreate(CamelModel):
    key: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=255)
    owner: str = Field(min_length=1, max_length=255)
    framework: str = Field(min_length=1, max_length=64)
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


class ModelDetailResponse(ModelResponse):
    versions: list[ModelVersionResponse] = Field(default_factory=list)
