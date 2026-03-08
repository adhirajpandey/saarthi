"""Geofence endpoints."""

import logging

from fastapi import APIRouter, Depends

from app.dependencies.auth import require_admin_token
from app.dependencies.config import get_settings
from app.api.schemas import GeofenceEventRequest, GeofenceEventResponse
from app.errors import AppError
from app.services.geofence import send_geofence_notification
from shared.settings import ApiSettings

router = APIRouter(prefix="/geofence", tags=["Geofence"])
logger = logging.getLogger(__name__)


@router.post(
    "/events",
    response_model=GeofenceEventResponse,
    dependencies=[Depends(require_admin_token)],
)
async def create_geofence_event(
    payload: GeofenceEventRequest,
    settings: ApiSettings = Depends(get_settings),
) -> GeofenceEventResponse:
    """Receive geofence update and send email notification."""
    logger.info(f"Geofence event received - Area: {payload.area}, Event: {payload.event}")

    result = await send_geofence_notification(
        settings=settings,
        area=payload.area,
        event=payload.event,
    )

    if result.success:
        return GeofenceEventResponse(
            success=True,
            message=result.message,
        )

    raise AppError(
        status_code=500,
        code="notification_failed",
        message=result.message,
    )
