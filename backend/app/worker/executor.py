"""Executes a claimed deployment through its state machine.

Pure enough to unit-test on SQLite: given a claimed (VALIDATING) deployment, it
advances to a terminal state and records an event per step. The `sleep` and
`deploy_seconds` params make the simulated work instant in tests.
"""
import time
from collections.abc import Callable

import structlog
from sqlalchemy.orm import Session

from app.core.enums import DeploymentStatus
from app.core.logging import get_logger
from app.models.deployment import Deployment
from app.models.model import ModelVersion
from app.services.deployment_policy import is_deployable
from app.worker import queue

logger = get_logger("worker")


def _fail(db: Session, deployment: Deployment, event: str, message: str) -> None:
    deployment.status = DeploymentStatus.FAILED
    deployment.error = event
    deployment.locked_at = None
    queue.record_event(db, deployment, event, message=message, actor="worker")
    db.commit()
    logger.warning("deployment_failed", failure=event)


def process_deployment(
    db: Session,
    deployment: Deployment,
    *,
    sleep: Callable[[float], None] = time.sleep,
    deploy_seconds: float = 1.0,
) -> Deployment:
    """Advance a claimed deployment (VALIDATING) to SUCCEEDED or FAILED."""
    # Re-bind the correlation id across the API -> worker boundary.
    if deployment.correlation_id:
        structlog.contextvars.bind_contextvars(correlation_id=deployment.correlation_id)
    structlog.contextvars.bind_contextvars(deployment_id=str(deployment.id))
    try:
        queue.record_event(db, deployment, "validation_started", actor="worker")
        db.commit()

        version = db.get(ModelVersion, deployment.model_version_id)
        deployable = version is not None and is_deployable(
            version.stage, deployment.environment
        )
        if not deployable:
            _fail(db, deployment, "approval_validation_failed", "version not deployable")
            return deployment

        deployment.status = DeploymentStatus.DEPLOYING
        queue.record_event(db, deployment, "deployment_started", actor="worker")
        db.commit()
        logger.info("deployment_deploying")

        sleep(deploy_seconds)  # simulate the long-running deploy

        if deployment.simulate_failure:
            _fail(db, deployment, "runtime_timeout", "simulated failure")
            return deployment

        deployment.status = DeploymentStatus.SUCCEEDED
        deployment.error = None
        deployment.locked_at = None
        queue.record_event(db, deployment, "deployment_completed", actor="worker")
        db.commit()
        logger.info("deployment_succeeded")
        return deployment
    finally:
        structlog.contextvars.clear_contextvars()
