"""Integration tests for the model registry API."""
import uuid

from tests.conftest import auth_header

MODEL = {
    "name": "Pump Failure Predictor",
    "owner": "Reliability AI Team",
    "framework": "scikit-learn",
    "tags": {"domain": "reliability"},
}
VERSION = {
    "version": "1.0.0",
    "artifactUri": "s3://models/pump/1.0.0",
    "algorithm": "random-forest",
    "trainingDataRef": "s3://data/pump/2026-07",
}


def _create_model(client, hdr):
    resp = client.post("/models", json=MODEL, headers=hdr)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _create_version(client, hdr, model_id, version="1.0.0"):
    resp = client.post(
        f"/models/{model_id}/versions", json={**VERSION, "version": version}, headers=hdr
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# --- happy path / CRUD ---

def test_create_and_get_model_with_versions(client):
    eng = auth_header(client, "engineer")
    model_id = _create_model(client, eng)
    _create_version(client, eng, model_id, "1.0.0")
    _create_version(client, eng, model_id, "2.0.0")

    detail = client.get(f"/models/{model_id}", headers=eng).json()
    assert detail["key"] == "pump-failure-predictor"  # slug derived from name
    assert len(detail["versions"]) == 2
    # newest version first
    assert [v["version"] for v in detail["versions"]] == ["2.0.0", "1.0.0"]
    v = detail["versions"][0]
    assert v["stage"] == "DRAFT"
    assert v["approved"] is False
    assert v["artifactUri"].startswith("s3://")  # camelCase contract


def test_list_models_visible_to_viewer(client):
    _create_model(client, auth_header(client, "engineer"))
    resp = client.get("/models", headers=auth_header(client, "viewer"))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1


def test_models_pagination(client):
    eng = auth_header(client, "engineer")
    for i in range(3):
        client.post("/models", json={**MODEL, "name": f"Model {i}"}, headers=eng)

    page1 = client.get("/models?limit=2&offset=0", headers=eng).json()
    assert page1["total"] == 3
    assert len(page1["items"]) == 2

    page2 = client.get("/models?limit=2&offset=2", headers=eng).json()
    assert len(page2["items"]) == 1
    # newest first, no overlap between pages
    ids = {m["id"] for m in page1["items"]} | {m["id"] for m in page2["items"]}
    assert len(ids) == 3


def test_models_server_side_search(client):
    eng = auth_header(client, "engineer")
    client.post("/models", json={**MODEL, "name": "Compressor Anomaly"}, headers=eng)
    client.post("/models", json={**MODEL, "name": "Pump Failure"}, headers=eng)

    resp = client.get("/models?q=compressor", headers=eng).json()
    assert resp["total"] == 1
    assert resp["items"][0]["name"] == "Compressor Anomaly"


def test_invalid_pagination_rejected(client):
    eng = auth_header(client, "engineer")
    assert client.get("/models?limit=0", headers=eng).status_code == 422
    assert client.get("/models?limit=500", headers=eng).status_code == 422


# --- lifecycle: full promotion to Production ---

def test_full_promotion_to_production(client):
    eng = auth_header(client, "engineer")
    appr = auth_header(client, "approver")
    model_id = _create_model(client, eng)
    vid = _create_version(client, eng, model_id)
    base = f"/models/{model_id}/versions/{vid}"

    def promote(stage):
        return client.post(f"{base}/promote", json={"targetStage": stage}, headers=appr)

    assert promote("VALIDATED").json()["stage"] == "VALIDATED"

    approved = client.post(f"{base}/approve", headers=appr).json()
    assert approved["stage"] == "APPROVED"
    assert approved["approved"] is True
    assert approved["approvedBy"] is not None

    assert promote("STAGING").json()["stage"] == "STAGING"
    assert promote("PRODUCTION").json()["stage"] == "PRODUCTION"


# --- lifecycle guards ---

def test_unapproved_version_cannot_reach_production(client):
    eng = auth_header(client, "engineer")
    appr = auth_header(client, "approver")
    model_id = _create_model(client, eng)
    vid = _create_version(client, eng, model_id)
    base = f"/models/{model_id}/versions/{vid}"

    client.post(f"{base}/promote", json={"targetStage": "VALIDATED"}, headers=appr)
    # VALIDATED -> PRODUCTION is illegal (must be approved + staged first)
    resp = client.post(f"{base}/promote", json={"targetStage": "PRODUCTION"}, headers=appr)
    assert resp.status_code == 409


def test_approve_requires_validated_stage(client):
    eng = auth_header(client, "engineer")
    appr = auth_header(client, "approver")
    model_id = _create_model(client, eng)
    vid = _create_version(client, eng, model_id)  # DRAFT
    resp = client.post(
        f"/models/{model_id}/versions/{vid}/approve", headers=appr
    )
    assert resp.status_code == 409  # DRAFT -> APPROVED illegal


# --- RBAC ---

def test_viewer_cannot_create_model(client):
    resp = client.post("/models", json=MODEL, headers=auth_header(client, "viewer"))
    assert resp.status_code == 403


def test_engineer_cannot_approve(client):
    eng = auth_header(client, "engineer")
    model_id = _create_model(client, eng)
    vid = _create_version(client, eng, model_id)
    resp = client.post(f"/models/{model_id}/versions/{vid}/approve", headers=eng)
    assert resp.status_code == 403


def test_unauthenticated_is_rejected(client):
    assert client.get("/models").status_code == 401


# --- conflicts / not found ---

def test_duplicate_name_gets_unique_slug(client):
    eng = auth_header(client, "engineer")
    first = client.post("/models", json=MODEL, headers=eng).json()
    second = client.post("/models", json=MODEL, headers=eng)
    assert second.status_code == 201  # no conflict — slug is uniquified
    assert first["key"] == "pump-failure-predictor"
    assert second.json()["key"] == "pump-failure-predictor-2"


def test_invalid_framework_rejected(client):
    eng = auth_header(client, "engineer")
    resp = client.post("/models", json={**MODEL, "framework": "cobol-ml"}, headers=eng)
    assert resp.status_code == 422  # not in the Framework enum


def test_duplicate_version_conflicts(client):
    eng = auth_header(client, "engineer")
    model_id = _create_model(client, eng)
    _create_version(client, eng, model_id, "1.0.0")
    resp = client.post(
        f"/models/{model_id}/versions", json={**VERSION, "version": "1.0.0"}, headers=eng
    )
    assert resp.status_code == 409


def test_get_unknown_model_404(client):
    resp = client.get(f"/models/{uuid.uuid4()}", headers=auth_header(client, "viewer"))
    assert resp.status_code == 404


def test_create_version_under_unknown_model_404(client):
    resp = client.post(
        f"/models/{uuid.uuid4()}/versions", json=VERSION, headers=auth_header(client, "engineer")
    )
    assert resp.status_code == 404
