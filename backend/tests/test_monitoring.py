"""Tests for the sample-data seeder and monitoring endpoints."""
import uuid

from app.db.seed_sample import seed_sample_data
from tests.conftest import auth_header


def _seed(db_session):
    db, _ = db_session
    return seed_sample_data(db)


def test_sample_seeder_loads_coherent_data(client, db_session):
    db, _ = db_session
    counts = _seed(db_session)
    assert counts["models"] == 2
    assert counts["versions"] == 4
    assert counts["deployments"] >= 3  # one per (version, env) with metrics + a failed one
    assert counts["metrics"] > 0
    # every metric is linked to the deployment that produced it
    from app.models.metric import Metric
    from sqlalchemy import func, select
    orphans = db.execute(
        select(func.count()).select_from(Metric).where(Metric.deployment_id.is_(None))
    ).scalar_one()
    assert orphans == 0
    # versions have lifecycle audit history; deployments have event timelines
    from app.models.deployment import DeploymentEvent
    from app.models.model import ModelVersionEvent
    assert db.execute(select(func.count()).select_from(ModelVersionEvent)).scalar_one() > 0
    assert db.execute(select(func.count()).select_from(DeploymentEvent)).scalar_one() > 0
    # idempotent — second run is a no-op
    assert seed_sample_data(db)["models"] == 0


def test_monitoring_overview(client, db_session):
    _seed(db_session)
    resp = client.get("/monitoring", headers=auth_header(client, "viewer"))
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 2
    item = items[0]
    assert item["monitoringStatus"] in {"HEALTHY", "DEGRADED", "NO_DATA"}
    assert item["latest"] is not None
    assert item["lastInferenceAt"] is not None


def test_model_metrics_summary(client, db_session):
    _seed(db_session)
    models = client.get("/models", headers=auth_header(client, "viewer")).json()["items"]
    model_id = models[0]["id"]
    resp = client.get(f"/models/{model_id}/metrics", headers=auth_header(client, "viewer"))
    assert resp.status_code == 200
    body = resp.json()
    assert body["latest"] is not None
    # camelCase metric fields
    assert "latencyMs" in body["latest"]
    assert "errorRate" in body["latest"]
    assert len(body["series"]) > 0
    # scoped to a (version, environment), with the available combos listed
    assert body["version"] is not None
    assert body["environment"] is not None
    assert len(body["available"]) >= 1


def test_model_metrics_scoped_to_version(client, db_session):
    _seed(db_session)
    models = client.get("/models", headers=auth_header(client, "viewer")).json()["items"]
    model_id = models[0]["id"]
    hdr = auth_header(client, "viewer")
    available = client.get(f"/models/{model_id}/metrics", headers=hdr).json()["available"]
    # pick a specific version+environment and confirm the series is scoped to it
    ref = available[0]
    body = client.get(
        f"/models/{model_id}/metrics",
        params={"version": ref["version"], "environment": ref["environment"]},
        headers=hdr,
    ).json()
    assert body["version"] == ref["version"]
    assert all(p["version"] == ref["version"] for p in body["series"])
    assert all(p["environment"] == ref["environment"] for p in body["series"])


def test_metrics_unknown_model_404(client):
    resp = client.get(f"/models/{uuid.uuid4()}/metrics", headers=auth_header(client, "viewer"))
    assert resp.status_code == 404


def test_monitoring_requires_auth(client):
    assert client.get("/monitoring").status_code == 401
