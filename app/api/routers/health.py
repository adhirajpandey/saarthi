"""Health endpoints."""

from fastapi import APIRouter, Request

from app.config.config import RATE_LIMIT_DEFAULT
from app.models import HealthCheckResponse
from app.utils.limiter import limiter
from app.utils.timezone import get_now_ist
from shared.logging import logger

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthCheckResponse)
@limiter.limit(RATE_LIMIT_DEFAULT)
async def health_check(request: Request) -> HealthCheckResponse:
    """Performs a basic health check, returns status and current IST time."""
    now_ist = get_now_ist()
    logger.info(f"Health check endpoint called. Current IST: {now_ist.isoformat()}")
    return HealthCheckResponse(status="ok", timestamp=now_ist)
