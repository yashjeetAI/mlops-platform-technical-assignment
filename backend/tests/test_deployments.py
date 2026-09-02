"""Integration tests for deployments: stage-gating, idempotency, worker, retry, rollback."""
import uuid

from app.worker import queue
from app.worker.executor import process_deployment
from tests.conftest import auth_header

MODEL = {"name": "Pump", "owner": "Team", "framework": "scikit-learn"}
VERSION = {"version": "1.0.0", "artifactUri": "s3://m/1.0.0"}

NOOP_SLEEP = lambda *_: None  # noqa: E731

# Forward lifecycle order (for promoting a version to a target stage in tests).
_FORWARD = ["DRAFT", "VALIDATED", "APPROVED", "STAGING", "PRODUCTION"]


def _new_model(client) -> str:
    eng = auth_header(client, "engineer")
    return client.post("/models", json={**MODEL, "name": f"m-{uuid.uuid4().hex[:6]}"}, headers=eng).json()["id"]


def _version_at_stage(client, stage, version="1.0.0", model_id=None):
    """Create a version and promote it forward to `stage`. Returns (model_id, version_id)."""
    eng = auth_header(client, "engineer")
    appr = auth_header(client, "approver")
    model_id = model_id or _new_model(client)
    vid = client.post(
        f"/models/{model_id}/versions", json={**VERSION, "version": version}, headers=eng
    ).json()["id"]

    def promote(target):
        client.post(
            f"/models/{model_id}/versions/{vid}/promote",
            json={"targetStage": target}, headers=appr,
        )

    idx = _FORWARD.index(stage)
    if idx >= 1:
        promote("VALIDATED")
    if idx >= 2:
        client.post(f"/models/{model_id}/versions/{vid}/approve", headers=appr)  # -> APPROVED
    if idx >= 3:
        promote("STAGING")
    if idx >= 4:
        promote("PRODUCTION")
    return model_id, vid


def _run_worker_once(db):
    """Claim and process a single queued deployment (instant, no real sleep)."""
    deployment = queue.claim_one(db, "test-worker")
    assert deployment is not None
    process_deployment(db, deployment, sleep=NOOP_SLEEP, deploy_seconds=0)
    return deployment


# --- stage-gating policy ---

def test_staging_version_deploys_to_staging(client):
    _, vid = _version_at_stage(client, "STAGING")
    eng = auth_header(client, "engineer")
    resp = client.post("/deployments", json={"modelVersionId": vid, "environment": "STAGING"}, headers=eng)
    assert resp.status_code == 202
    assert resp.json()["status"] == "REQUESTED"


def test_production_version_deploys_to_production(client):
    _, vid = _version_at_stage(client, "PRODUCTION")
    eng = auth_header(client, "engineer")
    resp = client.post("/deployments", json={"modelVersionId": vid, "environment": "PRODUCTION"}, headers=eng)
    assert resp.status_code == 202


def test_validated_version_deploys_to_development_only(client):
    _, vid = _version_at_stage(client, "VALIDATED")
    eng = auth_header(client, "engineer")
    assert client.post("/deployments", json={"modelVersionId": vid, "environment": "DEVELOPMENT"}, headers=eng).status_code == 202
    # not high enough for staging/production
    _, vid2 = _version_at_stage(client, "VALIDATED")
    assert client.post("/deployments", json={"modelVersionId": vid2, "environment": "STAGING"}, headers=eng).status_code == 409


def test_understaged_version_blocked_from_production(client):
    _, vid = _version_at_stage(client, "STAGING")  # STAGING stage, not PRODUCTION
    eng = auth_header(client, "engineer")
    resp = client.post("/deployments", json={"modelVersionId": vid, "environment": "PRODUCTION"}, headers=eng)
    assert resp.status_code == 409


def test_draft_version_not_deployable(client):
    eng = auth_header(client, "engineer")
    mid = _new_model(client)
    vid = client.post(f"/models/{mid}/versions", json=VERSION, headers=eng).json()["id"]  # DRAFT
    resp = client.post("/deployments", json={"modelVersionId": vid, "environment": "DEVELOPMENT"}, headers=eng)
    assert resp.status_code == 409


# --- idempotency + business guard ---

def test_second_inflight_deployment_same_model_env_conflicts(client):
    """A second in-flight deployment of the same model to the same env is rejected."""
    eng = auth_header(client, "engineer")
    mid, v1 = _version_at_stage(client, "PRODUCTION", version="1.0.0")
    _, v2 = _version_at_stage(client, "PRODUCTION", version="2.0.0", model_id=mid)

    first = client.post("/deployments", json={"modelVersionId": v1, "environment": "PRODUCTION"}, headers=eng)
    assert first.status_code == 202
    second = client.post("/deployments", json={"modelVersionId": v2, "environment": "PRODUCTION"}, headers=eng)
    assert second.status_code == 409


def test_can_deploy_same_model_to_different_env(client):
    """The guard is per-environment: same version to STAGING and PRODUCTION is allowed."""
    eng = auth_header(client, "engineer")
    _, vid = _version_at_stage(client, "PRODUCTION")  # deployable to both
    a = client.post("/deployments", json={"modelVersionId": vid, "environment": "STAGING"}, headers=eng)
    b = client.post("/deployments", json={"modelVersionId": vid, "environment": "PRODUCTION"}, headers=eng)
    assert a.status_code == 202 and b.status_code == 202


def test_duplicate_request_is_idempotent(client):
    _, vid = _version_at_stage(client, "STAGING")
    eng = auth_header(client, "engineer")
    payload = {"modelVersionId": vid, "environment": "STAGING", "idempotencyKey": "abc-123"}
    first = client.post("/deployments", json=payload, headers=eng)
    second = client.post("/deployments", json=payload, headers=eng)
    assert first.status_code == 202
    assert second.status_code == 200  # replay, not created
    assert first.json()["id"] == second.json()["id"]
    page = client.get("/deployments", headers=eng).json()
    assert page["total"] == 1
    assert page["items"][0]["version"] == "1.0.0"  # enriched for display
    assert page["items"][0]["modelKey"] is not None


# --- worker execution ---

def test_worker_completes_deployment(client, db_session):
    db, _ = db_session
    _, vid = _version_at_stage(client, "STAGING")
    eng = auth_header(client, "engineer")
    dep = client.post("/deployments", json={"modelVersionId": vid, "environment": "STAGING"}, headers=eng).json()

    _run_worker_once(db)

    got = client.get(f"/deployments/{dep['id']}", headers=eng).json()
    assert got["status"] == "SUCCEEDED"
    assert "deployment_completed" in [e["event"] for e in got["events"]]


def test_worker_fails_on_simulated_failure(client, db_session):
    db, _ = db_session
    _, vid = _version_at_stage(client, "STAGING")
    eng = auth_header(client, "engineer")
    dep = client.post(
        "/deployments",
        json={"modelVersionId": vid, "environment": "STAGING", "simulateFailure": True},
        headers=eng,
    ).json()

    _run_worker_once(db)

    got = client.get(f"/deployments/{dep['id']}", headers=eng).json()
    assert got["status"] == "FAILED"
    assert got["error"] == "runtime_timeout"


# --- retry ---

def test_retry_failed_deployment_then_succeeds(client, db_session):
    db, _ = db_session
    _, vid = _version_at_stage(client, "STAGING")
    eng = auth_header(client, "engineer")
    dep = client.post(
        "/deployments",
        json={"modelVersionId": vid, "environment": "STAGING", "simulateFailure": True},
        headers=eng,
    ).json()
    _run_worker_once(db)  # -> FAILED

    from app.models.deployment import Deployment
    row = db.get(Deployment, uuid.UUID(dep["id"]))
    row.simulate_failure = False
    db.commit()

    retried = client.post(f"/deployments/{dep['id']}/retry", headers=eng)
    assert retried.status_code == 200
    assert retried.json()["status"] == "REQUESTED"

    _run_worker_once(db)  # -> SUCCEEDED
    got = client.get(f"/deployments/{dep['id']}", headers=eng).json()
    assert got["status"] == "SUCCEEDED"


def test_retry_non_failed_conflicts(client):
    _, vid = _version_at_stage(client, "STAGING")
    eng = auth_header(client, "engineer")
    dep = client.post("/deployments", json={"modelVersionId": vid, "environment": "STAGING"}, headers=eng).json()
    resp = client.post(f"/deployments/{dep['id']}/retry", headers=eng)
    assert resp.status_code == 409  # still REQUESTED


# --- rollback ---

def test_rollback_to_previous_successful(client, db_session):
    db, _ = db_session
    admin = auth_header(client, "admin")
    eng = auth_header(client, "engineer")
    mid = _new_model(client)

    def deploy(version):
        _, vid = _version_at_stage(client, "PRODUCTION", version=version, model_id=mid)
        dep = client.post("/deployments", json={"modelVersionId": vid, "environment": "PRODUCTION"}, headers=eng).json()
        _run_worker_once(db)
        return dep["id"]

    first = deploy("1.0.0")
    second = deploy("2.0.0")

    resp = client.post(f"/deployments/{second}/rollback", headers=admin)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ROLLED_BACK"
    assert body["rolledBackToId"] == first


def test_rollback_without_previous_conflicts(client, db_session):
    db, _ = db_session
    _, vid = _version_at_stage(client, "PRODUCTION")
    eng = auth_header(client, "engineer")
    admin = auth_header(client, "admin")
    dep = client.post("/deployments", json={"modelVersionId": vid, "environment": "PRODUCTION"}, headers=eng).json()
    _run_worker_once(db)
    resp = client.post(f"/deployments/{dep['id']}/rollback", headers=admin)
    assert resp.status_code == 409  # nothing to roll back to


# --- RBAC ---

def test_viewer_cannot_request_deployment(client):
    _, vid = _version_at_stage(client, "STAGING")
    resp = client.post(
        "/deployments",
        json={"modelVersionId": vid, "environment": "STAGING"},
        headers=auth_header(client, "viewer"),
    )
    assert resp.status_code == 403


def test_engineer_cannot_rollback(client, db_session):
    db, _ = db_session
    _, vid = _version_at_stage(client, "PRODUCTION")
    eng = auth_header(client, "engineer")
    dep = client.post("/deployments", json={"modelVersionId": vid, "environment": "PRODUCTION"}, headers=eng).json()
    _run_worker_once(db)
    resp = client.post(f"/deployments/{dep['id']}/rollback", headers=eng)
    assert resp.status_code == 403
