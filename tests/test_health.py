"""API contract tests for health endpoint."""

from datetime import datetime
from unittest.mock import patch


def test_health_endpoint_returns_status_and_timestamp(client) -> None:
    with patch("app.api.routers.health.check_dell_home_connectivity", return_value=True):
        response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert datetime.fromisoformat(payload["timestamp"])
    assert payload["dell_home_connectivity"] is True


def test_health_endpoint_returns_false_when_connectivity_check_fails(client) -> None:
    with patch("app.api.routers.health.check_dell_home_connectivity", return_value=False):
        response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["dell_home_connectivity"] is False
