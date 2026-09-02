"""Model registry routes."""
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.enums import Role
from app.db.session import get_db
from app.models.user import User
from app.schemas.model import (
    ModelCreate,
    ModelDetailResponse,
    ModelResponse,
    ModelVersionCreate,
    ModelVersionResponse,
    StageChangeRequest,
)
from app.services import model_service

router = APIRouter(prefix="/models", tags=["models"])


@router.post("", response_model=ModelResponse, status_code=status.HTTP_201_CREATED)
def create_model(
    payload: ModelCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.ENGINEER)),
):
    return model_service.create_model(db, user.id, payload)


@router.get("", response_model=list[ModelResponse])
def list_models(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return model_service.list_models(db)


@router.get("/{model_id}", response_model=ModelDetailResponse)
def get_model(
    model_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return model_service.get_model(db, model_id)


@router.post(
    "/{model_id}/versions",
    response_model=ModelVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_version(
    model_id: uuid.UUID,
    payload: ModelVersionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.ENGINEER)),
):
    return model_service.create_version(db, user.id, model_id, payload)


@router.get("/{model_id}/versions", response_model=list[ModelVersionResponse])
def list_versions(
    model_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return model_service.list_versions(db, model_id)


@router.post(
    "/{model_id}/versions/{version_id}/approve",
    response_model=ModelVersionResponse,
)
def approve_version(
    model_id: uuid.UUID,
    version_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.APPROVER)),
):
    return model_service.approve_version(db, user.id, version_id)


@router.post(
    "/{model_id}/versions/{version_id}/promote",
    response_model=ModelVersionResponse,
)
def promote_version(
    model_id: uuid.UUID,
    version_id: uuid.UUID,
    payload: StageChangeRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.APPROVER)),
):
    return model_service.transition_version(db, version_id, payload.target_stage)
