"""Monitoring service: per-model metric summaries + a health overview."""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import Environment, MonitoringStatus
from app.models.metric import Metric
from app.services.model_service import get_model, list_models

# Thresholds for the health rollup.
_MIN_AVAILABILITY = 99.0
_MAX_ERROR_RATE = 0.03
_MAX_DRIFT = 0.30


def _status(latest: Metric | None) -> MonitoringStatus:
    if latest is None:
        return MonitoringStatus.NO_DATA
    if (
        latest.availability < _MIN_AVAILABILITY
        or latest.error_rate > _MAX_ERROR_RATE
        or latest.drift_score > _MAX_DRIFT
    ):
        return MonitoringStatus.DEGRADED
    return MonitoringStatus.HEALTHY


def _latest_metric(db: Session, model_id: uuid.UUID) -> Metric | None:
    return db.execute(
        select(Metric)
        .where(Metric.model_id == model_id)
        .order_by(Metric.timestamp.desc())
        .limit(1)
    ).scalar_one_or_none()


def _available_series(db: Session, model_id: uuid.UUID) -> list[tuple[str, Environment]]:
    """Distinct (version, environment) combinations that have metrics."""
    rows = db.execute(
        select(Metric.version, Metric.environment)
        .where(Metric.model_id == model_id)
        .distinct()
        .order_by(Metric.version.desc(), Metric.environment)
    ).all()
    return [(r.version, r.environment) for r in rows]


def get_model_metrics(
    db: Session,
    model_id: uuid.UUID,
    *,
    version: str | None = None,
    environment: Environment | None = None,
    points: int = 30,
) -> dict:
    """Monitoring summary scoped to a (version, environment).

    Metrics are per (model, version, environment); if version/environment are not
    given, defaults to the combination of the most recent sample.
    """
    model = get_model(db, model_id)  # 404 if missing
    available = _available_series(db, model_id)

    if version is None or environment is None:
        latest_any = _latest_metric(db, model_id)
        if latest_any is not None:
            version = version or latest_any.version
            environment = environment or latest_any.environment

    query = select(Metric).where(Metric.model_id == model_id)
    if version is not None:
        query = query.where(Metric.version == version)
    if environment is not None:
        query = query.where(Metric.environment == environment)

    latest = db.execute(query.order_by(Metric.timestamp.desc()).limit(1)).scalar_one_or_none()
    recent = list(
        db.execute(query.order_by(Metric.timestamp.desc()).limit(points)).scalars()
    )
    recent.reverse()  # chronological for charting

    return {
        "model_id": model.id,
        "model_key": model.key,
        "name": model.name,
        "monitoring_status": _status(latest),
        "last_inference_at": latest.timestamp if latest else None,
        "version": version,
        "environment": environment,
        "latest": latest,
        "series": recent,
        "available": [{"version": v, "environment": e} for v, e in available],
    }


def list_monitoring(db: Session) -> list[dict]:
    """Health overview across all models (latest sample + status each)."""
    overview = []
    for model in list_models(db, limit=1000)[0]:
        latest = _latest_metric(db, model.id)
        overview.append(
            {
                "model_id": model.id,
                "model_key": model.key,
                "name": model.name,
                "monitoring_status": _status(latest),
                "last_inference_at": latest.timestamp if latest else None,
                "latest": latest,
            }
        )
    return overview
