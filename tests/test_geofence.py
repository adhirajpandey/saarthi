"""Tests for geofence endpoint authentication.

Tests that the geofence endpoint only accepts admin token.
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app

class TestGeofenceAuth:
    """Test geofence endpoint authentication."""

    @pytest.fixture
    def client(self):
        with TestClient(app) as test_client:
            yield test_client

    @pytest.fixture(autouse=True)
    def mock_email(self):
        """Mock email sending to avoid actual emails during tests."""
        with patch("app.services.geofence.send_email", return_value=True):
            yield

    def test_geofence_with_valid_admin_token(self, client: TestClient):
        """Test geofence accepts valid admin token."""
        response = client.post(
            "/geofence/events",
            json={"area": "Home", "event": "entered"},
            headers={"Authorization": "Bearer test-admin-token"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Home" in data["message"]

    def test_geofence_with_invalid_token(self, client: TestClient):
        """Test geofence rejects invalid token."""
        response = client.post(
            "/geofence/events",
            json={"area": "Home", "event": "entered"},
            headers={"Authorization": "Bearer invalid-token-12345"},
        )
        
        assert response.status_code == 401
        assert response.json()["error"]["message"] == "Invalid admin token"

    def test_geofence_without_token(self, client: TestClient):
        """Test geofence rejects request without token."""
        response = client.post(
            "/geofence/events",
            json={"area": "Home", "event": "entered"},
        )
        
        assert response.status_code == 401
        assert response.json()["error"]["message"] == "Missing bearer token"

    def test_geofence_any_success_when_email_fails(self, client: TestClient):
        settings = client.app.state.settings
        settings.whatsapp_enabled = True
        settings.whatsapp_ssh_host = "pookie"
        settings.whatsapp_remote_script_path = "/home/pookie/.openclaw/workspace/scripts/send_whatsapp_message.py"
        settings.whatsapp_target_family = "120363369409471870@g.us"

        with (
            patch("app.services.geofence.send_email", return_value=False),
            patch("app.services.geofence.send_whatsapp_message", return_value=True),
        ):
            response = client.post(
                "/geofence/events",
                json={"area": "Home", "event": "entered"},
                headers={"Authorization": "Bearer test-admin-token"},
            )

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_geofence_fails_when_all_channels_fail(self, client: TestClient):
        settings = client.app.state.settings
        settings.whatsapp_enabled = True
        settings.whatsapp_ssh_host = "pookie"
        settings.whatsapp_remote_script_path = "/home/pookie/.openclaw/workspace/scripts/send_whatsapp_message.py"
        settings.whatsapp_target_family = "120363369409471870@g.us"

        with (
            patch("app.services.geofence.send_email", return_value=False),
            patch("app.services.geofence.send_whatsapp_message", return_value=False),
        ):
            response = client.post(
                "/geofence/events",
                json={"area": "Home", "event": "entered"},
                headers={"Authorization": "Bearer test-admin-token"},
            )

        assert response.status_code == 500
        assert response.json()["error"]["code"] == "notification_failed"
