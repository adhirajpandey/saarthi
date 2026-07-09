"""Health endpoints."""

import logging

from fastapi import APIRouter

from app.api.schemas import HealthCheckResponse

router = APIRouter(tags=["Health"])
logger = logging.getLogger(__name__)


@router.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """Return a minimal liveness response."""
    logger.info("Health check endpoint called.")
    return HealthCheckResponse(status="healthy")
