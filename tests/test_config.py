"""Tests for configuration loading.

These tests verify that the CONFIG object loads correctly with expected values.
"""

import os
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestConfig:
    """Test configuration values match expected settings."""

    def test_base_config(self):
        """Test base configuration values."""
        from app import CONFIG

        assert CONFIG.base.app_name == "SAARTHI"

    def test_jwt_config(self):
        """Test JWT configuration values."""
        from app import CONFIG

        assert CONFIG.jwt.algorithm == "HS256"
        assert CONFIG.jwt.access_token_expire_minutes == 30

    def test_rate_limiting_config(self):
        """Test rate limiting configuration defaults."""
        from app import CONFIG

        assert CONFIG.rate_limiting.default_limit == "50/minute"
        assert CONFIG.rate_limiting.login_limit == "5/minute"
        assert CONFIG.rate_limiting.chat_limit == "10/minute"

    def test_ai_service_models(self):
        """Test AI service models are loaded correctly."""
        from app import CONFIG

        models = CONFIG.ai_service.models
        assert len(models) == 7

        # Check first model (highest priority - openrouter)
        openrouter_model = next(m for m in models if m.provider == "openrouter")
        assert openrouter_model.name == "mistralai/mistral-7b-instruct:free"
        assert openrouter_model.priority == 0

        # Check ollama models exist
        ollama_models = [m for m in models if m.provider == "ollama"]
        assert len(ollama_models) == 2
        assert any(m.name == "qwen3:0.6b" for m in ollama_models)
        assert any(m.name == "qwen3:4b" for m in ollama_models)

        # Check openai models exist
        openai_models = [m for m in models if m.provider == "openai"]
        assert len(openai_models) == 2

        # Check gemini models exist
        gemini_models = [m for m in models if m.provider == "gemini"]
        assert len(gemini_models) == 2
