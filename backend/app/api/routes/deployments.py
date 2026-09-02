"""Deployment routes."""
import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.api.middleware import get_correlation_id
from app.core.enums import Role
from app.db.session import get_db
from app.models.user import User
from app.schemas.deployment import (
    DeploymentCreate,
    DeploymentDetailResponse,
    DeploymentPage,
)
from app.services import deployment_service

router = APIRouter(prefix="/deployments", tags=["deployments"])


@router.post("", response_model=DeploymentDetailResponse)
def request_deployment(
    payload: DeploymentCreate,
    request_response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.ENGINEER)),
):
    deployment, created = deployment_service.request_deployment(
        db, user.id, get_correlation_id(), payload
    )
    # 202 Accepted for a newly-queued deployment; 200 for an idempotent replay.
    request_response.status_code = (
        status.HTTP_202_ACCEPTED if created else status.HTTP_200_OK
    )
    return deployment


@router.get("", response_model=DeploymentPage)
def list_deployments(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None, description="Search model/version/environment/status"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    items, total = deployment_service.list_deployments(db, limit=limit, offset=offset, q=q)
    return DeploymentPage(items=items, total=total, limit=limit, offset=offset)


@router.get("/{deployment_id}", response_model=DeploymentDetailResponse)
def get_deployment(
    deployment_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return deployment_service.get_deployment(db, deployment_id)


@router.post("/{deployment_id}/retry", response_model=DeploymentDetailResponse)
def retry_deployment(
    deployment_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.ENGINEER)),
):
    return deployment_service.retry_deployment(db, user.id, deployment_id)


@router.post("/{deployment_id}/rollback", response_model=DeploymentDetailResponse)
def rollback_deployment(
    deployment_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.ADMIN)),
):
    return deployment_service.rollback_deployment(db, user.id, deployment_id)
