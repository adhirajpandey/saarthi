"""API contract tests for health endpoint."""

from datetime import datetime


def test_health_endpoint_returns_status_and_timestamp(client) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert datetime.fromisoformat(payload["timestamp"])
