"""Tests for me location endpoint."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from app.services.location import StoredLocation

def test_me_location_requires_token(client) -> None:
    response = client.post(
        "/me/location",
        json={"latitude": 12.9716, "longitude": 77.5946},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_me_location_returns_success_payload(client) -> None:
    now = datetime.now(UTC)
    save_mock = AsyncMock(return_value=StoredLocation(id=99, timestamp=now))
    engine_mock = AsyncMock(return_value=None)

    with (
        patch("app.api.routers.me.save_location_ping", save_mock),
        patch("app.api.routers.me.run_geofence_engine", engine_mock),
    ):
        response = client.post(
            "/me/location",
            json={"latitude": 12.9716, "longitude": 77.5946},
            headers={"Authorization": "Bearer test-admin-token"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["id"] == 99
    assert datetime.fromisoformat(payload["timestamp"].replace("Z", "+00:00")) == now
    save_mock.assert_awaited_once()
    engine_mock.assert_awaited_once()


def test_me_location_rejects_invalid_coordinates(client) -> None:
    response = client.post(
        "/me/location",
        json={"latitude": 120.0, "longitude": 77.5946},
        headers={"Authorization": "Bearer test-admin-token"},
    )

    assert response.status_code == 422


def test_me_location_returns_500_when_insert_fails(client) -> None:
    with patch("app.api.routers.me.save_location_ping", side_effect=RuntimeError("db down")):
        response = client.post(
            "/me/location",
            json={"latitude": 12.9716, "longitude": 77.5946},
            headers={"Authorization": "Bearer test-admin-token"},
        )

    assert response.status_code == 500
    payload = response.json()
    assert payload["error"]["code"] == "location_persist_failed"


def test_me_location_enqueues_geofence_engine(client) -> None:
    now = datetime.now(UTC)
    save_mock = AsyncMock(return_value=StoredLocation(id=1, timestamp=now))
    engine_mock = AsyncMock(return_value=None)
    with (
        patch("app.api.routers.me.save_location_ping", save_mock),
        patch("app.api.routers.me.run_geofence_engine", engine_mock),
    ):
        response = client.post(
            "/me/location",
            json={"latitude": 12.9716, "longitude": 77.5946},
            headers={"Authorization": "Bearer test-admin-token"},
        )

    assert response.status_code == 200
    save_mock.assert_awaited_once()
    engine_mock.assert_awaited_once()
    assert engine_mock.await_args.kwargs["db_path"] == client.app.state.settings.location_db_path
    assert engine_mock.await_args.kwargs["mapping"] == client.app.state.geofence_mapping
