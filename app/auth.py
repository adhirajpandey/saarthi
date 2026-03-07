from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app import CONFIG
from .utils.logging import logger


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def require_admin_token(token: Annotated[str, Depends(oauth2_scheme)]) -> str:
    """Dependency that validates the admin token.

    All endpoints requiring authentication use this single dependency.
    The admin token is a long-lived secret set via the ADMIN_TOKEN env var.
    """
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

    logger.debug("Authenticated via admin token")
    return "admin"
