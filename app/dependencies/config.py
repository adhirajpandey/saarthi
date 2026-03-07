"""Configuration dependency helpers."""

from fastapi import Request

from app.models import SharedConfig


def get_config(request: Request) -> SharedConfig:
    """Return application configuration from app state."""
    return request.app.state.config
