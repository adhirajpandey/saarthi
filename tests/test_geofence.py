"""API contract tests for geofence endpoint."""

from unittest.mock import AsyncMock, patch

from app.services.geofence import NotificationResult


def test_geofence_accepts_valid_admin_token(client) -> None:
    with patch(
        "app.api.routers.geofence.send_geofence_notification",
        AsyncMock(return_value=NotificationResult(success=True, message="ok")),
    ):
        response = client.post(
            "/geofence/events",
            json={"area": "Home", "event": "entered"},
            headers={"Authorization": "Bearer test-admin-token"},
        )

    assert response.status_code == 200
    assert response.json() == {"success": True, "message": "ok"}


def test_geofence_rejects_invalid_token(client) -> None:
    response = client.post(
        "/geofence/events",
        json={"area": "Home", "event": "entered"},
        headers={"Authorization": "Bearer invalid-token-12345"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Invalid admin token"


def test_geofence_rejects_missing_token(client) -> None:
    response = client.post(
        "/geofence/events",
        json={"area": "Home", "event": "entered"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Missing bearer token"


def test_geofence_returns_500_on_service_failure(client) -> None:
    with patch(
        "app.api.routers.geofence.send_geofence_notification",
        AsyncMock(return_value=NotificationResult(success=False, message="dispatch failed")),
    ):
        response = client.post(
            "/geofence/events",
            json={"area": "Home", "event": "entered"},
            headers={"Authorization": "Bearer test-admin-token"},
        )

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "notification_failed"
