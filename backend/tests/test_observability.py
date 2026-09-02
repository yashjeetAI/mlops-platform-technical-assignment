"""Tests for correlation-id middleware."""
from app.api.middleware import CORRELATION_HEADER


def test_correlation_id_added_to_response(client):
    resp = client.get("/health")
    assert resp.headers.get(CORRELATION_HEADER)


def test_correlation_id_echoed_when_provided(client):
    rid = "trace-abc-123"
    resp = client.get("/health", headers={CORRELATION_HEADER: rid})
    assert resp.headers.get(CORRELATION_HEADER) == rid


def test_correlation_id_is_unique_per_request(client):
    a = client.get("/health").headers.get(CORRELATION_HEADER)
    b = client.get("/health").headers.get(CORRELATION_HEADER)
    assert a and b and a != b
