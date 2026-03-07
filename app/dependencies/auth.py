"""Authentication dependencies."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app import CONFIG
from shared.logging import logger


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def require_admin_token(token: Annotated[str, Depends(oauth2_scheme)]) -> str:
    """Dependency that validates the admin token."""
    admin_token = CONFIG.admin_token

    if not admin_token:
        logger.error("Admin token auth requested but ADMIN_TOKEN not configured")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin token auth not configured",
        )

    if token != admin_token:
        logger.warning("Invalid admin token provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token",
        )

    return "admin"

