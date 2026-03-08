"""Configuration dependency helpers."""

from fastapi import Request

from shared.settings import ApiSettings


def get_settings(request: Request) -> ApiSettings:
    """Return API settings from app state."""
    return request.app.state.settings
