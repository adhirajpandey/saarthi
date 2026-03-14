"""Health endpoints."""

import logging

from fastapi import APIRouter, Request

from app.api.schemas import HealthCheckResponse
from app.services.connectivity import check_dell_home_connectivity
from app.utils.timezone import get_now_ist

router = APIRouter(tags=["Health"])
logger = logging.getLogger(__name__)


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(request: Request) -> HealthCheckResponse:
    """Performs a basic health check, returns status and current IST time."""
    now_ist = get_now_ist()
    settings = request.app.state.settings
    dell_home_connectivity = check_dell_home_connectivity(settings.dell_tailscale_ip)
    logger.info(f"Health check endpoint called. Current IST: {now_ist.isoformat()}")
    return HealthCheckResponse(
        status="ok",
        timestamp=now_ist,
        dell_home_connectivity=dell_home_connectivity,
    )
