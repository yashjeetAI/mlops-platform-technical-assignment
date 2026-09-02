"""Deployment service: request (idempotent), retry, rollback, queries.

Enqueuing is atomic — inserting the REQUESTED row IS the enqueue (no dual write) —
then a best-effort NOTIFY wakes the worker; the poller is the safety net.
"""
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import DeploymentStatus, Environment
from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.models.deployment import Deployment
from app.models.model import Model, ModelVersion
from app.schemas.deployment import DeploymentCreate
from app.services.deployment_policy import is_deployable
from app.worker import queue

logger = get_logger("deployments")


def get_deployment(db: Session, deployment_id: uuid.UUID) -> Deployment:
    deployment = db.get(Deployment, deployment_id)
    if deployment is None:
        raise NotFoundError(f"Deployment {deployment_id} not found")
    return deployment


def list_deployments(
    db: Session, *, limit: int = 20, offset: int = 0, q: str | None = None
) -> tuple[list[Deployment], int]:
    """Return (page of deployments, total), newest first.

    `q` filters (case-insensitive) across model key/name, version, environment and status.
    """
    stmt = select(Deployment)
    count_stmt = select(func.count()).select_from(Deployment)
    if q:
        pattern = f"%{q}%"
        # Join model + version to search their human-readable fields.
        stmt = stmt.join(Model, Deployment.model_id == Model.id).join(
            ModelVersion, Deployment.model_version_id == ModelVersion.id
        )
        count_stmt = count_stmt.join(Model, Deployment.model_id == Model.id).join(
            ModelVersion, Deployment.model_version_id == ModelVersion.id
        )
        cond = or_(
            Model.key.ilike(pattern),
            Model.name.ilike(pattern),
            ModelVersion.version.ilike(pattern),
            Deployment.environment.ilike(pattern),
            Deployment.status.ilike(pattern),
        )
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)

    total = db.execute(count_stmt).scalar_one()
    items = list(
        db.execute(
            stmt.order_by(Deployment.id.desc()).offset(offset).limit(limit)
        ).scalars()
    )
    return items, total


def _assert_deployable(version: ModelVersion, environment: Environment) -> None:
    """Governance gate: the version's lifecycle stage must allow this environment."""
    if not is_deployable(version.stage, environment):
        raise ConflictError(
            f"A {version.stage.value} version cannot be deployed to {environment.value}"
        )


def request_deployment(
    db: Session,
    actor_id: uuid.UUID,
    correlation_id: str | None,
    data: DeploymentCreate,
) -> tuple[Deployment, bool]:
    """Create a deployment (REQUESTED). Returns (deployment, created).

    If `idempotency_key` matches an existing deployment, returns that one with
    created=False (safe duplicate handling).
    """
    if data.idempotency_key:
        existing = db.execute(
            select(Deployment).where(Deployment.idempotency_key == data.idempotency_key)
        ).scalar_one_or_none()
        if existing is not None:
            logger.info("deployment_idempotent_hit", deployment_id=str(existing.id))
            return existing, False

    version = db.get(ModelVersion, data.model_version_id)
    if version is None:
        raise NotFoundError(f"Model version {data.model_version_id} not found")
    _assert_deployable(version, data.environment)

    deployment = Deployment(
        model_id=version.model_id,
        model_version_id=data.model_version_id,
        environment=data.environment,
        status=DeploymentStatus.REQUESTED,
        idempotency_key=data.idempotency_key,
        simulate_failure=data.simulate_failure,
        correlation_id=correlation_id,
        created_by=actor_id,
    )
    db.add(deployment)
    try:
        db.flush()  # assign id; enforces the in-flight uniqueness index
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            f"A deployment for this model is already in progress in {data.environment.value}"
        ) from exc
    queue.record_event(db, deployment, "requested", actor=str(actor_id))
    db.commit()
    db.refresh(deployment)

    queue.notify(db)  # best-effort push; poller is the safety net
    logger.info(
        "deployment_requested",
        deployment_id=str(deployment.id),
        environment=deployment.environment.value,
    )
    return deployment, True


def retry_deployment(db: Session, actor_id: uuid.UUID, deployment_id: uuid.UUID) -> Deployment:
    """Re-queue a FAILED deployment."""
    deployment = get_deployment(db, deployment_id)
    if deployment.status != DeploymentStatus.FAILED:
        raise ConflictError(
            f"Only FAILED deployments can be retried (status is {deployment.status.value})"
        )
    deployment.status = DeploymentStatus.REQUESTED
    deployment.error = None
    deployment.worker_id = None
    deployment.locked_at = None
    queue.record_event(db, deployment, "retry_requested", actor=str(actor_id))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            "Another deployment for this model is already in progress in "
            f"{deployment.environment.value}"
        ) from exc
    db.refresh(deployment)

    queue.notify(db)
    logger.info("deployment_retry", deployment_id=str(deployment.id))
    return deployment


def rollback_deployment(
    db: Session, actor_id: uuid.UUID, deployment_id: uuid.UUID
) -> Deployment:
    """Roll back a SUCCEEDED deployment to the previous good one in the same env.

    Safety: refuses if there is no earlier successful deployment of a different
    version to fall back to.
    """
    deployment = get_deployment(db, deployment_id)
    if deployment.status != DeploymentStatus.SUCCEEDED:
        raise ConflictError(
            f"Only SUCCEEDED deployments can be rolled back (status is {deployment.status.value})"
        )

    # "Previous" is determined by the time-ordered UUIDv7 id (created earlier),
    # which is monotonic across DBs (SQLite created_at is only second-resolution).
    # Uses the denormalized model_id, so no join is needed.
    target = db.execute(
        select(Deployment)
        .where(
            Deployment.environment == deployment.environment,
            Deployment.status == DeploymentStatus.SUCCEEDED,
            Deployment.model_id == deployment.model_id,
            Deployment.model_version_id != deployment.model_version_id,
            Deployment.id < deployment.id,
        )
        .order_by(Deployment.id.desc())
        .limit(1)
    ).scalar_one_or_none()

    if target is None:
        raise ConflictError("No previous successful deployment to roll back to")

    deployment.status = DeploymentStatus.ROLLED_BACK
    deployment.rolled_back_to_id = target.id
    queue.record_event(
        db,
        deployment,
        "rolled_back",
        message=f"rolled back to deployment {target.id}",
        actor=str(actor_id),
    )
    db.commit()
    db.refresh(deployment)
    logger.info(
        "deployment_rolled_back",
        deployment_id=str(deployment.id),
        rolled_back_to=str(target.id),
    )
    return deployment
