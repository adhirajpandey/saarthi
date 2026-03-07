"""Geofence endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.dependencies.auth import require_admin_token
from app.dependencies.config import get_config
from app.models import SharedConfig
from app.services.email import send_geofence_notification
from shared.logging import logger

router = APIRouter(prefix="/geofence", tags=["Geofence"])


class GeofenceRequest(BaseModel):
    """Request model for geofence updates."""

    area: str
    trigger: str


class GeofenceResponse(BaseModel):
    """Response model for geofence updates."""

    success: bool
    message: str


@router.post("", response_model=GeofenceResponse, dependencies=[Depends(require_admin_token)])
async def geofence_update(
    request: Request,
    payload: GeofenceRequest,
    config: SharedConfig = Depends(get_config),
) -> GeofenceResponse:
    """Receive geofence update and send email notification."""
    logger.info(f"Geofence update received - Area: {payload.area}, Trigger: {payload.trigger}")

    success = send_geofence_notification(
        geofence_config=config.geofence,
        area=payload.area,
        trigger=payload.trigger,
    )

    if success:
        return GeofenceResponse(
            success=True,
            message=f"Geofence notification sent for {payload.area}",
        )

    raise HTTPException(
        status_code=500,
        detail="Failed to send geofence notification email",
    )
