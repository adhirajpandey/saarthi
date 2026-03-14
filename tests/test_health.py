"""API contract tests for health endpoint."""

from datetime import datetime
from unittest.mock import patch


def test_health_endpoint_returns_status_and_timestamp(client) -> None:
    with (
        patch("app.api.routers.health.check_tailscale_available", return_value=True),
        patch("app.api.routers.health.check_rclone_available", return_value=True),
        patch("app.api.routers.health.check_pg_dump_available", return_value=True),
        patch("app.api.routers.health.check_dell_home_connectivity", return_value=True),
    ):
        response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert datetime.fromisoformat(payload["timestamp"])
    assert payload["dell_home_connectivity"] is True
    assert payload["tailscale_available"] is True
    assert payload["rclone_available"] is True
    assert payload["pg_dump_available"] is True


def test_health_endpoint_skips_ping_when_tailscale_is_unavailable(client) -> None:
    with (
        patch("app.api.routers.health.check_tailscale_available", return_value=False),
        patch("app.api.routers.health.check_rclone_available", return_value=True),
        patch("app.api.routers.health.check_pg_dump_available", return_value=True),
        patch("app.api.routers.health.check_dell_home_connectivity") as ping_mock,
    ):
        response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["dell_home_connectivity"] is False
    assert payload["tailscale_available"] is False
    assert payload["rclone_available"] is True
    assert payload["pg_dump_available"] is True
    ping_mock.assert_not_called()


def test_health_endpoint_returns_mixed_tool_availability(client) -> None:
    with (
        patch("app.api.routers.health.check_tailscale_available", return_value=True),
        patch("app.api.routers.health.check_rclone_available", return_value=False),
        patch("app.api.routers.health.check_pg_dump_available", return_value=True),
        patch("app.api.routers.health.check_dell_home_connectivity", return_value=True),
    ):
        response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["dell_home_connectivity"] is True
    assert payload["tailscale_available"] is True
    assert payload["rclone_available"] is False
    assert payload["pg_dump_available"] is True
