"""Pytest configuration and fixtures."""

import os

# Set test environment variables BEFORE any app imports.
# This is necessary because configuration loads at module import time.
env_vars = {
    "ADMIN_TOKEN": "test-admin-token",
    "GEOFENCE_UPDATES_RECIPIENT": "test@example.com",
    "GEOFENCE_SENDER_NAME": "Test Sender",
}
for key, value in env_vars.items():
    os.environ.setdefault(key, value)
