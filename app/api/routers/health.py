"""Health endpoints."""

import logging

from fastapi import APIRouter, Request

from app.api.schemas import HealthCheckResponse
from app.services.connectivity import (
    check_dell_home_connectivity,
    check_pg_dump_available,
    check_rclone_available,
    check_tailscale_available,
)
from app.utils.timezone import get_now_ist

router = APIRouter(tags=["Health"])
logger = logging.getLogger(__name__)


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(request: Request) -> HealthCheckResponse:
    """Performs a basic health check, returns status and current IST time."""
    now_ist = get_now_ist()
    settings = request.app.state.settings
    tailscale_available = check_tailscale_available()
    rclone_available = check_rclone_available()
    pg_dump_available = check_pg_dump_available()
    dell_home_connectivity = (
        check_dell_home_connectivity(settings.dell_tailscale_ip) if tailscale_available else False
    )
    logger.info(f"Health check endpoint called. Current IST: {now_ist.isoformat()}")
    return HealthCheckResponse(
        status="ok",
        timestamp=now_ist,
        dell_home_connectivity=dell_home_connectivity,
        tailscale_available=tailscale_available,
        rclone_available=rclone_available,
        pg_dump_available=pg_dump_available,
    )
