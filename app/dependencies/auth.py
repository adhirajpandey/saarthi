"""Authentication dependencies."""

import secrets
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.dependencies.config import get_settings
from app.errors import AppError
from shared.settings import ApiSettings
from shared.logging import logger


http_bearer = HTTPBearer(auto_error=False)


async def require_admin_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(http_bearer)],
    settings: Annotated[ApiSettings, Depends(get_settings)],
) -> str:
    """Dependency that validates the admin token."""
    if credentials is None:
        raise AppError(status_code=401, code="unauthorized", message="Missing bearer token")

    if not secrets.compare_digest(credentials.credentials, settings.admin_token):
        logger.warning("Invalid admin token provided")
        raise AppError(status_code=401, code="unauthorized", message="Invalid admin token")

    return "admin"
