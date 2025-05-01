from datetime import datetime, timedelta, timezone  # Use timezone.utc for JWT
from typing import Optional, Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import ValidationError  # Import Pydantic's validation error

from .config import CONFIG
import os
from .core import logger

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
    """Dependency to get the current user from a JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
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
    except (
        ValidationError
    ) as e:  # Catch Pydantic errors if payload structure is somehow invalid after decode
        logger.warning(f"Token payload validation error: {e}. Token: {token[:10]}...")
        raise credentials_exception

    logger.debug(f"Token validated successfully for user: {username}")
    return username  # Return username (or user object in a real app)
