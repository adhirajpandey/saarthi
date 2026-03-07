"""Health endpoints."""

from fastapi import APIRouter, Request

from app import CONFIG
from app.models import HealthCheckResponse
from app.utils.limiter import limiter
from app.utils.timezone import get_now_ist
from shared.logging import logger

router = APIRouter(tags=["Health"])

HEALTH_RATE_LIMIT = CONFIG.rate_limiting


@router.get("/health", response_model=HealthCheckResponse)
@limiter.limit(HEALTH_RATE_LIMIT.default_limit)
async def health_check(request: Request) -> HealthCheckResponse:
    """Performs a basic health check, returns status and current IST time."""
    now_ist = get_now_ist()
    logger.info(f"Health check endpoint called. Current IST: {now_ist.isoformat()}")
    return HealthCheckResponse(status="ok", timestamp=now_ist)

