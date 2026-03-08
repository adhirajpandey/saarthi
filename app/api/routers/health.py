"""Health endpoints."""

import logging

from fastapi import APIRouter

from app.api.schemas import HealthCheckResponse
from app.utils.timezone import get_now_ist

router = APIRouter(tags=["Health"])
logger = logging.getLogger(__name__)


@router.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """Performs a basic health check, returns status and current IST time."""
    now_ist = get_now_ist()
    logger.info(f"Health check endpoint called. Current IST: {now_ist.isoformat()}")
    return HealthCheckResponse(status="ok", timestamp=now_ist)
