"""Tests for authentication and role-based authorization."""
import pytest
from fastapi import Depends

from app.api.deps import require_roles
from app.core.enums import Role
from app.main import app
from tests.conftest import auth_header


def test_login_success_returns_token(client):
    resp = client.post("/auth/login", json={"username": "admin", "password": "demo1234"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["tokenType"] == "bearer"
    assert body["accessToken"]


def test_login_wrong_password_401(client):
    resp = client.post("/auth/login", json={"username": "admin", "password": "nope"})
    assert resp.status_code == 401


def test_login_unknown_user_401(client):
    resp = client.post("/auth/login", json={"username": "ghost", "password": "demo1234"})
    assert resp.status_code == 401


def test_me_requires_token(client):
    assert client.get("/auth/me").status_code == 401


def test_me_returns_current_user(client):
    resp = client.get("/auth/me", headers=auth_header(client, "engineer"))
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "engineer"
    assert body["role"] == "ENGINEER"
    assert "hashed_password" not in body
    # camelCase API contract
    assert "fullName" in body and "createdAt" in body
    assert "full_name" not in body


def test_me_rejects_garbage_token(client):
    resp = client.get("/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert resp.status_code == 401


# --- RBAC guard: mount a temporary protected route for the test ---

@app.get("/_test/approver-only")
def _approver_only(user=Depends(require_roles(Role.APPROVER))):
    return {"ok": True, "user": user.username}


@pytest.mark.parametrize(
    "username,expected",
    [
        ("approver", 200),  # allowed
        ("admin", 200),     # admin always allowed
        ("engineer", 403),  # insufficient role
        ("viewer", 403),
    ],
)
def test_require_roles_enforced(client, username, expected):
    resp = client.get("/_test/approver-only", headers=auth_header(client, username))
    assert resp.status_code == expected
