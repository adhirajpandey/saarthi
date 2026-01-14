"""Tests for geofence endpoint authentication.

Tests that the geofence endpoint only accepts admin token.
"""

import os
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


class TestGeofenceAuth:
    """Test geofence endpoint authentication."""

    @pytest.fixture(autouse=True)
    def mock_email(self):
        """Mock email sending to avoid actual emails during tests."""
        with patch("app.services.email.send_email", return_value=True):
            yield

    @pytest.fixture
    def mock_admin_token(self):
        """Mock admin token in CONFIG for tests that require it."""
        with patch("app.auth.CONFIG") as mock_config:
            mock_config.admin_token = "test-admin-token"
            yield mock_config

    def test_geofence_with_valid_admin_token(self, mock_admin_token):
        """Test geofence accepts valid admin token."""
        response = client.post(
            "/geofence",
            json={"area": "Home", "trigger": "entered"},
            headers={"Authorization": "Bearer test-admin-token"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Home" in data["message"]

    def test_geofence_with_invalid_token(self, mock_admin_token):
        """Test geofence rejects invalid token."""
        response = client.post(
            "/geofence",
            json={"area": "Home", "trigger": "entered"},
            headers={"Authorization": "Bearer invalid-token-12345"},
        )
        
        assert response.status_code == 401
        assert "Invalid admin token" in response.json()["detail"]

    def test_geofence_without_token(self):
        """Test geofence rejects request without token."""
        response = client.post(
            "/geofence",
            json={"area": "Home", "trigger": "entered"},
        )
        
        assert response.status_code == 401
