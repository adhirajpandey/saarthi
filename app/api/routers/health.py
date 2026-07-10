"""Health endpoints."""

import logging

from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool

from app.api.schemas import HealthCheckResponse
from app.services.health import collect_health_state

router = APIRouter(tags=["Health"])
logger = logging.getLogger(__name__)


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(request: Request) -> HealthCheckResponse:
    """Return cached coarse runtime availability."""
    logger.info("Health check endpoint called.")
    settings = request.app.state.settings
    mapping = request.app.state.geofence_mapping

    async def load_response() -> HealthCheckResponse:
        return await run_in_threadpool(collect_health_state, settings, mapping)

    return await request.app.state.health_response_cache.get(load_response)
