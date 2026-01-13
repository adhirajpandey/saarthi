"""Pytest configuration and fixtures."""

import pytest


@pytest.fixture(scope="function", autouse=True)
def setup_test_env(monkeypatch):
    """Set test environment variables. Cleanup is automatic via monkeypatch."""
    env_vars = {
        "JWT_SECRET_KEY": "test-secret-key",
        "OLLAMA_DELL_WORK_ENDPOINT": "http://localhost:11434",
        "OLLAMA_DELL_WORK_API_KEY": "test-key",
        "GEMINI_ENDPOINT": "http://localhost:8080",
        "GEMINI_API_KEY": "test-key",
        "OPENROUTER_ENDPOINT": "http://localhost:8081",
        "OPENROUTER_API_KEY": "test-key",
    }
    
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
