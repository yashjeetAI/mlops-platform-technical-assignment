"""Load the provided sample data as a coherent dataset.

Seeds registry (models + versions) with lifecycle audit events, then the
deployments that produced the metrics (with their event timelines), then the
metrics linked to those deployments. Idempotent: only seeds an empty registry.
Also runnable on demand: `python -m app.db.seed_sample`.
"""
import csv
import json
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import DeploymentStatus, Environment, LifecycleStage as S
from app.core.logging import get_logger
from app.models.deployment import Deployment, DeploymentEvent
from app.models.metric import Metric
from app.models.mixins import utcnow
from app.models.model import Model, ModelVersion, ModelVersionEvent
from app.models.user import User

logger = get_logger("seed")

# Forward lifecycle a version passed through to reach its seeded stage.
_STAGE_CHAIN: dict[S, list[S]] = {
    S.DRAFT: [],
    S.VALIDATED: [S.VALIDATED],
    S.APPROVED: [S.VALIDATED, S.APPROVED],
    S.STAGING: [S.VALIDATED, S.APPROVED, S.STAGING],
    S.PRODUCTION: [S.VALIDATED, S.APPROVED, S.STAGING, S.PRODUCTION],
    S.ARCHIVED: [S.VALIDATED, S.APPROVED, S.STAGING, S.PRODUCTION, S.ARCHIVED],
}


def _data_dir() -> Path:
    configured = get_settings().seed_data_dir
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[3] / "data"


def _user_id(db: Session, username: str) -> uuid.UUID | None:
    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    return user.id if user else None


def _event_name(frm: S | None, to: S) -> str:
    if to == S.ARCHIVED:
        return "archived"
    if frm is None:
        return "created"
    if to == S.APPROVED:
        return "approved"
    if to == S.VALIDATED:
        return "validated"
    return "promoted"


def _record_lifecycle(db, version, stage, engineer_id, approver_id) -> None:
    db.add(ModelVersionEvent(
        model_version_id=version.id, event="created",
        from_stage=None, to_stage=S.DRAFT, actor_id=engineer_id,
    ))
    prev = S.DRAFT
    for st in _STAGE_CHAIN[stage]:
        db.add(ModelVersionEvent(
            model_version_id=version.id, event=_event_name(prev, st),
            from_stage=prev, to_stage=st, actor_id=approver_id,
        ))
        prev = st


_SUCCESS_STEPS = [
    (DeploymentStatus.REQUESTED, "requested"),
    (DeploymentStatus.VALIDATING, "validation_started"),
    (DeploymentStatus.DEPLOYING, "deployment_started"),
    (DeploymentStatus.SUCCEEDED, "deployment_completed"),
]


def _make_deployment(db, model, version, environment, status, error=None, actor_id=None):
    dep = Deployment(
        model_id=model.id, model_version_id=version.id, environment=environment,
        status=status, error=error, created_by=actor_id,
        attempts=1,  # these were executed once (a real run increments attempts on claim)
    )
    db.add(dep)
    db.flush()
    if status == DeploymentStatus.SUCCEEDED:
        for st, name in _SUCCESS_STEPS:
            db.add(DeploymentEvent(deployment_id=dep.id, status=st, event=name, actor="worker"))
    else:  # failed
        db.add(DeploymentEvent(deployment_id=dep.id, status=DeploymentStatus.REQUESTED, event="requested", actor="worker"))
        db.add(DeploymentEvent(deployment_id=dep.id, status=status, event=error or "failed", actor="worker"))
    return dep


def seed_sample_data(db: Session) -> dict[str, int]:
    """Seed the coherent sample dataset. Returns counts (all zero if skipped)."""
    if db.execute(select(func.count()).select_from(Model)).scalar_one() > 0:
        return {"models": 0, "versions": 0, "deployments": 0, "metrics": 0}

    data_dir = _data_dir()
    engineer_id = _user_id(db, "engineer")
    approver_id = _user_id(db, "approver")

    models_by_key: dict[str, Model] = {}
    versions_by_key: dict[tuple[str, str], ModelVersion] = {}
    counts = {"models": 0, "versions": 0, "deployments": 0, "metrics": 0}

    # 1) Registry + version lifecycle audit history.
    for spec in json.loads((data_dir / "models.json").read_text()):
        model = Model(
            key=spec["model_id"], name=spec["name"], owner=spec["owner"],
            framework=spec["framework"], tags={}, created_by=engineer_id,
        )
        db.add(model)
        db.flush()
        models_by_key[spec["model_id"]] = model
        counts["models"] += 1
        for vspec in spec.get("versions", []):
            stage = S(vspec["stage"])
            approved = bool(vspec.get("approved"))
            version = ModelVersion(
                model_id=model.id, version=vspec["version"], stage=stage,
                artifact_uri=vspec["artifact_uri"], tags={}, created_by=engineer_id,
                approved_at=utcnow() if approved else None,
                approved_by=approver_id if approved else None,
            )
            db.add(version)
            db.flush()
            versions_by_key[(spec["model_id"], vspec["version"])] = version
            _record_lifecycle(db, version, stage, engineer_id, approver_id)
            counts["versions"] += 1

    # 2) Deployments (one SUCCEEDED per version+env with metrics) + linked metrics.
    deployments_by_combo: dict[tuple[uuid.UUID, Environment], Deployment] = {}
    with (data_dir / "metrics.csv").open() as f:
        for row in csv.DictReader(f):
            version = versions_by_key.get((row["model_id"], row["version"]))
            if version is None:
                continue  # skip metrics for versions not in the registry
            env = Environment(row["environment"].upper())
            combo = (version.id, env)
            dep = deployments_by_combo.get(combo)
            if dep is None:
                dep = _make_deployment(
                    db, models_by_key[row["model_id"]], version, env,
                    DeploymentStatus.SUCCEEDED, actor_id=engineer_id,
                )
                deployments_by_combo[combo] = dep
                counts["deployments"] += 1
            db.add(Metric(
                model_id=version.model_id, model_version_id=version.id,
                deployment_id=dep.id, version=row["version"], environment=env,
                timestamp=datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00")),
                latency_ms=float(row["latency_ms"]),
                throughput_rpm=float(row["throughput_rpm"]),
                error_rate=float(row["error_rate"]),
                quality_score=float(row["quality_score"]),
                drift_score=float(row["drift_score"]),
                availability=float(row["availability"]),
            ))
            counts["metrics"] += 1

    # 3) Failed deployments from the sample events (a metric-less, failed attempt).
    events_path = data_dir / "deployment_events.json"
    if events_path.exists():
        for e in json.loads(events_path.read_text()):
            if e["status"] == "SUCCEEDED":
                continue  # covered by the metric-derived deployments
            model = models_by_key.get(e["model_id"])
            version = versions_by_key.get((e["model_id"], e["version"]))
            if model is None or version is None:
                continue
            _make_deployment(
                db, model, version, Environment(e["environment"].upper()),
                DeploymentStatus(e["status"]), error=e["event"], actor_id=engineer_id,
            )
            counts["deployments"] += 1

    db.commit()
    logger.info("sample_data_seeded", **counts)
    return counts


if __name__ == "__main__":  # pragma: no cover
    from app.db.migrations import upgrade_to_head
    from app.db.session import SessionLocal

    upgrade_to_head()
    with SessionLocal() as session:
        print(seed_sample_data(session))
