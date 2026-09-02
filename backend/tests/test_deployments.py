"""Integration tests for deployments: request, idempotency, worker, retry, rollback."""
import uuid

from app.worker import queue
from app.worker.executor import process_deployment
from tests.conftest import auth_header

MODEL = {"key": "pump", "name": "Pump", "owner": "Team", "framework": "scikit-learn"}
VERSION = {"version": "1.0.0", "artifactUri": "s3://m/1.0.0"}

NOOP_SLEEP = lambda *_: None  # noqa: E731


def _make_version(client, approve=False, version="1.0.0"):
    """Create a model + version; optionally approve it. Returns version id."""
    eng = auth_header(client, "engineer")
    appr = auth_header(client, "approver")
    # a fresh model per call keeps versions independent
    key = f"model-{version}-{uuid.uuid4().hex[:6]}"
    mid = client.post("/models", json={**MODEL, "key": key}, headers=eng).json()["id"]
    vid = client.post(
        f"/models/{mid}/versions", json={**VERSION, "version": version}, headers=eng
    ).json()["id"]
    if approve:
        client.post(f"/models/{mid}/versions/{vid}/promote", json={"targetStage": "VALIDATED"}, headers=appr)
        client.post(f"/models/{mid}/versions/{vid}/approve", headers=appr)
    return vid


def _run_worker_once(db):
    """Claim and process a single queued deployment (instant, no real sleep)."""
    deployment = queue.claim_one(db, "test-worker")
    assert deployment is not None
    process_deployment(db, deployment, sleep=NOOP_SLEEP, deploy_seconds=0)
    return deployment


# --- request + queueing ---

def test_request_deployment_is_queued(client):
    vid = _make_version(client)
    eng = auth_header(client, "engineer")
    resp = client.post(
        "/deployments", json={"modelVersionId": vid, "environment": "STAGING"}, headers=eng
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "REQUESTED"
    assert any(e["event"] == "requested" for e in body["events"])


def test_production_requires_approved_version(client):
    vid = _make_version(client, approve=False)
    eng = auth_header(client, "engineer")
    resp = client.post(
        "/deployments", json={"modelVersionId": vid, "environment": "PRODUCTION"}, headers=eng
    )
    assert resp.status_code == 409


def test_approved_version_deploys_to_production(client):
    vid = _make_version(client, approve=True)
    eng = auth_header(client, "engineer")
    resp = client.post(
        "/deployments", json={"modelVersionId": vid, "environment": "PRODUCTION"}, headers=eng
    )
    assert resp.status_code == 202


# --- idempotency ---

def test_second_inflight_deployment_same_model_env_conflicts(client):
    """Business guard: even with a different key/version, a second in-flight
    deployment of the same model to the same env is rejected (model+env)."""
    eng = auth_header(client, "engineer")
    appr = auth_header(client, "approver")
    key = f"m-{uuid.uuid4().hex[:6]}"
    mid = client.post("/models", json={**MODEL, "key": key}, headers=eng).json()["id"]

    def approved_version(v):
        vid = client.post(f"/models/{mid}/versions", json={**VERSION, "version": v}, headers=eng).json()["id"]
        client.post(f"/models/{mid}/versions/{vid}/promote", json={"targetStage": "VALIDATED"}, headers=appr)
        client.post(f"/models/{mid}/versions/{vid}/approve", headers=appr)
        return vid

    v1, v2 = approved_version("1.0.0"), approved_version("2.0.0")
    first = client.post("/deployments", json={"modelVersionId": v1, "environment": "PRODUCTION"}, headers=eng)
    assert first.status_code == 202
    # different version, no idempotency key -> still blocked while v1 is in flight
    second = client.post("/deployments", json={"modelVersionId": v2, "environment": "PRODUCTION"}, headers=eng)
    assert second.status_code == 409


def test_can_deploy_same_model_to_different_env(client):
    """The guard is per-environment: same model to STAGING and PRODUCTION is allowed."""
    eng = auth_header(client, "engineer")
    vid = _make_version(client, approve=True)
    a = client.post("/deployments", json={"modelVersionId": vid, "environment": "STAGING"}, headers=eng)
    b = client.post("/deployments", json={"modelVersionId": vid, "environment": "PRODUCTION"}, headers=eng)
    assert a.status_code == 202 and b.status_code == 202


def test_duplicate_request_is_idempotent(client):
    vid = _make_version(client)
    eng = auth_header(client, "engineer")
    payload = {"modelVersionId": vid, "environment": "STAGING", "idempotencyKey": "abc-123"}
    first = client.post("/deployments", json=payload, headers=eng)
    second = client.post("/deployments", json=payload, headers=eng)
    assert first.status_code == 202
    assert second.status_code == 200  # replay, not created
    assert first.json()["id"] == second.json()["id"]
    assert len(client.get("/deployments", headers=eng).json()) == 1


# --- worker execution ---

def test_worker_completes_deployment(client, db_session):
    db, _ = db_session
    vid = _make_version(client)
    eng = auth_header(client, "engineer")
    dep = client.post(
        "/deployments", json={"modelVersionId": vid, "environment": "STAGING"}, headers=eng
    ).json()

    _run_worker_once(db)

    got = client.get(f"/deployments/{dep['id']}", headers=eng).json()
    assert got["status"] == "SUCCEEDED"
    events = [e["event"] for e in got["events"]]
    assert "deployment_completed" in events


def test_worker_fails_on_simulated_failure(client, db_session):
    db, _ = db_session
    vid = _make_version(client)
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
    vid = _make_version(client)
    eng = auth_header(client, "engineer")
    dep = client.post(
        "/deployments",
        json={"modelVersionId": vid, "environment": "STAGING", "simulateFailure": True},
        headers=eng,
    ).json()
    _run_worker_once(db)  # -> FAILED

    # clear the failure flag directly, then retry
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
    vid = _make_version(client)
    eng = auth_header(client, "engineer")
    dep = client.post(
        "/deployments", json={"modelVersionId": vid, "environment": "STAGING"}, headers=eng
    ).json()
    # still REQUESTED -> cannot retry
    resp = client.post(f"/deployments/{dep['id']}/retry", headers=eng)
    assert resp.status_code == 409


# --- rollback ---

def test_rollback_to_previous_successful(client, db_session):
    db, _ = db_session
    admin = auth_header(client, "admin")
    eng = auth_header(client, "engineer")
    # same model, two approved versions, both deployed to production successfully
    appr = auth_header(client, "approver")
    key = f"m-{uuid.uuid4().hex[:6]}"
    mid = client.post("/models", json={**MODEL, "key": key}, headers=eng).json()["id"]

    def deploy(version):
        vid = client.post(f"/models/{mid}/versions", json={**VERSION, "version": version}, headers=eng).json()["id"]
        client.post(f"/models/{mid}/versions/{vid}/promote", json={"targetStage": "VALIDATED"}, headers=appr)
        client.post(f"/models/{mid}/versions/{vid}/approve", headers=appr)
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
    vid = _make_version(client, approve=True)
    eng = auth_header(client, "engineer")
    admin = auth_header(client, "admin")
    dep = client.post(
        "/deployments", json={"modelVersionId": vid, "environment": "PRODUCTION"}, headers=eng
    ).json()
    _run_worker_once(db)
    resp = client.post(f"/deployments/{dep['id']}/rollback", headers=admin)
    assert resp.status_code == 409  # nothing to roll back to


# --- RBAC ---

def test_viewer_cannot_request_deployment(client):
    vid = _make_version(client)
    resp = client.post(
        "/deployments",
        json={"modelVersionId": vid, "environment": "STAGING"},
        headers=auth_header(client, "viewer"),
    )
    assert resp.status_code == 403


def test_engineer_cannot_rollback(client, db_session):
    db, _ = db_session
    vid = _make_version(client, approve=True)
    eng = auth_header(client, "engineer")
    dep = client.post(
        "/deployments", json={"modelVersionId": vid, "environment": "PRODUCTION"}, headers=eng
    ).json()
    _run_worker_once(db)
    resp = client.post(f"/deployments/{dep['id']}/rollback", headers=eng)
    assert resp.status_code == 403
