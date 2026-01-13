from datetime import datetime, timedelta, timezone  # Use timezone.utc for JWT
from typing import Optional, Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import ValidationError  # Import Pydantic's validation error

from app import CONFIG
import os
from .utils.logging import logger

jwt_config = CONFIG.jwt


# --- Constants from Config ---
SECRET_KEY = jwt_config.secret_key
ALGORITHM = jwt_config.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = jwt_config.access_token_expire_minutes

MOCK_USERS_DB = {
    os.getenv("DUMMY_USERNAME", "adhirja"): os.getenv("DUMMY_PASSWORD", "password"),
}


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def verify_password(plain_password, hashed_password_from_db):
    """Verifies a plain password against a stored password (mock version)."""
    if plain_password == hashed_password_from_db:
        return True
    else:
        logger.debug("Password verification failed (plain text comparison).")
        return False


def get_user_password(username: str) -> Optional[str]:
    """Retrieves user password from mock DB."""
    return MOCK_USERS_DB.get(username)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Creates a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta  # Use UTC for expiration
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update(
        {"exp": expire}
    )  # 'exp' claim is standard, seconds since epoch (UTC)
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> str:
    """Dependency to get the current user from a JWT token or static API token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    
    # Check if it's the static API token first
    static_token = CONFIG.static_api_token
    if static_token and token == static_token:
        logger.debug("Authenticated via static API token")
        return "adhiraj-lt-token"
    
    # Fall back to JWT validation
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if username is None:
            logger.warning(
                f"Token validation failed: username (sub) missing. Token: {token[:10]}..."
            )
            raise credentials_exception
    except JWTError as e:
        logger.warning(f"Token validation JWTError: {e}. Token: {token[:10]}...")
        raise credentials_exception from e
    except ValidationError as e:  # Catch Pydantic errors if payload structure is somehow invalid after decode
        logger.warning(f"Token payload validation error: {e}. Token: {token[:10]}...")
        raise credentials_exception

    logger.debug(f"Token validated successfully for user: {username}")
    return username  # Return username (or user object in a real app)


async def require_static_token(token: Annotated[str, Depends(oauth2_scheme)]) -> str:
    """Dependency that only accepts static API token (not JWT).
    
    Use this for endpoints that should only be accessible via long-term
    static token, like the geofence endpoint called from MacroDroid.
    """
    static_token = CONFIG.static_api_token
    
    if not static_token:
        logger.error("Static token auth requested but STATIC_API_TOKEN not configured")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Static token auth not configured",
        )
    
    if token != static_token:
        logger.warning("Invalid static token provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid static token",
        )
    
    logger.debug("Authenticated via static API token")
    return "static-token-user"
