"""Pytest configuration and fixtures."""

import os

# Set test environment variables BEFORE any app imports.
# This is necessary because configuration loads at module import time.
os.environ.setdefault("ADMIN_TOKEN", "test-admin-token")
os.environ.setdefault("OLLAMA_DELL_WORK_ENDPOINT", "http://localhost:11434")
os.environ.setdefault("OLLAMA_DELL_WORK_API_KEY", "test-key")
os.environ.setdefault("GEMINI_ENDPOINT", "http://localhost:8080")
os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ.setdefault("OPENROUTER_ENDPOINT", "http://localhost:8081")
os.environ.setdefault("OPENROUTER_API_KEY", "test-key")
os.environ.setdefault("GEOFENCE_UPDATES_RECIPIENT", "test@example.com")
os.environ.setdefault("GEOFENCE_SENDER_NAME", "Test Sender")
