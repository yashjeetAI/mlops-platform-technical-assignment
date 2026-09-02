"""Load the provided sample data (models, versions, metrics) into the database.

Idempotent: only seeds when the registry is empty, so it populates a fresh
`docker compose up` without touching an existing DB. Also runnable on demand:
`python -m app.db.seed_sample`.
"""
import csv
import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import Environment, LifecycleStage
from app.core.logging import get_logger
from app.models.metric import Metric
from app.models.mixins import utcnow
from app.models.model import Model, ModelVersion

logger = get_logger("seed")


def _data_dir() -> Path:
    """Resolve the sample-data directory (env/setting override, else repo-root data/)."""
    configured = get_settings().seed_data_dir
    if configured:
        return Path(configured)
    # backend/app/db/seed_sample.py -> repo root -> data/
    return Path(__file__).resolve().parents[3] / "data"


def seed_sample_data(db: Session) -> dict[str, int]:
    """Seed sample models/versions/metrics. Returns counts (all zero if skipped)."""
    if db.execute(select(func.count()).select_from(Model)).scalar_one() > 0:
        return {"models": 0, "versions": 0, "metrics": 0}

    models_by_key: dict[str, Model] = {}
    versions_by_key: dict[tuple[str, str], ModelVersion] = {}

    data_dir = _data_dir()
    registry = json.loads((data_dir / "models.json").read_text())
    models = versions = 0
    for spec in registry:
        model = Model(
            key=spec["model_id"],
            name=spec["name"],
            owner=spec["owner"],
            framework=spec["framework"],
            tags={},
        )
        db.add(model)
        db.flush()
        models_by_key[spec["model_id"]] = model
        models += 1
        for vspec in spec.get("versions", []):
            version = ModelVersion(
                model_id=model.id,
                version=vspec["version"],
                stage=LifecycleStage(vspec["stage"]),
                artifact_uri=vspec["artifact_uri"],
                tags={},
                approved_at=utcnow() if vspec.get("approved") else None,
            )
            db.add(version)
            db.flush()
            versions_by_key[(spec["model_id"], vspec["version"])] = version
            versions += 1

    metrics = 0
    with (data_dir / "metrics.csv").open() as f:
        for row in csv.DictReader(f):
            model = models_by_key.get(row["model_id"])
            if model is None:
                continue
            mv = versions_by_key.get((row["model_id"], row["version"]))
            db.add(
                Metric(
                    model_id=model.id,
                    model_version_id=mv.id if mv else None,
                    version=row["version"],
                    environment=Environment(row["environment"].upper()),
                    timestamp=datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00")),
                    latency_ms=float(row["latency_ms"]),
                    throughput_rpm=float(row["throughput_rpm"]),
                    error_rate=float(row["error_rate"]),
                    quality_score=float(row["quality_score"]),
                    drift_score=float(row["drift_score"]),
                    availability=float(row["availability"]),
                )
            )
            metrics += 1

    db.commit()
    counts = {"models": models, "versions": versions, "metrics": metrics}
    logger.info("sample_data_seeded", **counts)
    return counts


if __name__ == "__main__":  # pragma: no cover
    from app.db.migrations import upgrade_to_head
    from app.db.session import SessionLocal

    upgrade_to_head()
    with SessionLocal() as session:
        print(seed_sample_data(session))
