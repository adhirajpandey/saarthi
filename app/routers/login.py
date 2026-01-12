from datetime import timedelta
from fastapi import APIRouter, Request, HTTPException, status
from ..models import Token, UserLogin
from ..auth import (
    verify_password,
    get_user_password,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from ..utils.limiter import limiter
from ..utils.logging import logger
from ..config import CONFIG


router = APIRouter(tags=["Authentication"])

# Get rate limit string from config
LOGIN_RATE_LIMIT = CONFIG.rate_limiting.login_limit


@router.post("/login", response_model=Token)
@limiter.limit(LOGIN_RATE_LIMIT)
async def login_for_access_token_json(
    request: Request,  # Needed for rate limiter state
    user_credentials: UserLogin,
):
    """
    Authenticates user via JSON request body and returns a JWT access token.
    Expects: {"username": "...", "password": "..."}
    """
    logger.info(f"Login attempt via JSON for user: {user_credentials.username}")
    user_pw_from_db = get_user_password(user_credentials.username)

    if not user_pw_from_db or not verify_password(
        user_credentials.password, user_pw_from_db
    ):
        logger.warning(f"Failed login attempt for user: {user_credentials.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_credentials.username}, expires_delta=access_token_expires
    )
    logger.info(f"Successful login for user: {user_credentials.username}")
    return {"access_token": access_token, "token_type": "bearer"}
