"""Tests for geofence endpoint authentication.

Tests that the geofence endpoint only accepts static API token.
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

    def test_geofence_with_valid_static_token(self):
        """Test geofence accepts valid static token."""
        from app import CONFIG
        
        token = CONFIG.static_api_token
        if not token:
            pytest.skip("STATIC_API_TOKEN not configured")
        
        response = client.post(
            "/geofence",
            json={"area": "Home", "trigger": "entered"},
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Home" in data["message"]

    def test_geofence_with_invalid_token(self):
        """Test geofence rejects invalid token."""
        response = client.post(
            "/geofence",
            json={"area": "Home", "trigger": "entered"},
            headers={"Authorization": "Bearer invalid-token-12345"},
        )
        
        assert response.status_code == 401
        assert "Invalid static token" in response.json()["detail"]

    def test_geofence_without_token(self):
        """Test geofence rejects request without token."""
        response = client.post(
            "/geofence",
            json={"area": "Home", "trigger": "entered"},
        )
        
        assert response.status_code == 401

    def test_geofence_rejects_jwt_token(self):
        """Test geofence rejects JWT token (only static token allowed)."""
        from app.auth import create_access_token
        
        # Create a valid JWT token
        jwt_token = create_access_token(data={"sub": "testuser"})
        
        response = client.post(
            "/geofence",
            json={"area": "Home", "trigger": "entered"},
            headers={"Authorization": f"Bearer {jwt_token}"},
        )
        
        # JWT should be rejected - only static token is valid
        assert response.status_code == 401
        assert "Invalid static token" in response.json()["detail"]
