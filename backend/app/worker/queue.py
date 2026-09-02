"""DB-backed job-queue primitives over the `deployments` table.

Low-level and dependency-light (models only) so both the API service and the worker
executor can import it without cycles.
"""
from datetime import timedelta

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.enums import DeploymentStatus
from app.models.deployment import Deployment, DeploymentEvent
from app.models.mixins import utcnow

# Postgres LISTEN/NOTIFY channel used to wake workers on new work.
NOTIFY_CHANNEL = "deployments_new"

# Transient states a worker holds a job in; the reaper recovers these on crash.
STUCK_STATES = (DeploymentStatus.VALIDATING, DeploymentStatus.DEPLOYING)
MAX_ATTEMPTS = 3


def record_event(
    db: Session,
    deployment: Deployment,
    event: str,
    *,
    message: str | None = None,
    actor: str | None = None,
) -> None:
    """Append a DeploymentEvent (caller commits)."""
    db.add(
        DeploymentEvent(
            deployment_id=deployment.id,
            status=deployment.status,
            event=event,
            message=message,
            actor=actor,
            correlation_id=deployment.correlation_id,
        )
    )


def notify(db: Session) -> None:
    """Signal workers that new work exists (Postgres only; no-op otherwise)."""
    if db.bind is None or db.bind.dialect.name != "postgresql":
        return
    db.execute(text(f"NOTIFY {NOTIFY_CHANNEL}"))
    db.commit()


def claim_one(db: Session, worker_id: str) -> Deployment | None:
    """Atomically claim the oldest REQUESTED deployment.

    Uses FOR UPDATE SKIP LOCKED so multiple worker replicas never grab the same row.
    Moves it to VALIDATING and stamps worker/lock metadata (claim-and-release).
    """
    stmt = (
        select(Deployment)
        .where(Deployment.status == DeploymentStatus.REQUESTED)
        .order_by(Deployment.id)  # UUIDv7 is time-ordered
        .limit(1)
    )
    # Row-level lock is Postgres-only; SQLite (tests) runs single-connection.
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        stmt = stmt.with_for_update(skip_locked=True)
    deployment = db.execute(stmt).scalar_one_or_none()
    if deployment is None:
        return None
    deployment.status = DeploymentStatus.VALIDATING
    deployment.worker_id = worker_id
    deployment.locked_at = utcnow()
    deployment.attempts += 1
    db.commit()
    db.refresh(deployment)
    return deployment


def reap_stuck(db: Session, timeout_seconds: int = 120) -> int:
    """Recover jobs stuck in a transient state past the visibility timeout.

    Re-queues them (or fails them once attempts are exhausted). Returns count reaped.
    """
    cutoff = utcnow() - timedelta(seconds=timeout_seconds)
    stuck = (
        db.execute(
            select(Deployment).where(
                Deployment.status.in_(STUCK_STATES),
                Deployment.locked_at < cutoff,
            )
        )
        .scalars()
        .all()
    )
    for d in stuck:
        if d.attempts >= MAX_ATTEMPTS:
            d.status = DeploymentStatus.FAILED
            d.error = "worker_lost"
            record_event(db, d, "worker_lost", message="exceeded max attempts", actor="reaper")
        else:
            d.status = DeploymentStatus.REQUESTED
            d.worker_id = None
            d.locked_at = None
            record_event(db, d, "requeued", message="reclaimed after timeout", actor="reaper")
    if stuck:
        db.commit()
    return len(stuck)
