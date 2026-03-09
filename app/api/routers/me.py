"""Me endpoints."""

import logging
import sqlite3

from fastapi import APIRouter, BackgroundTasks, Depends, Request

from app.api.schemas import MeLocationRequest, MeLocationResponse
from app.dependencies.auth import require_admin_token
from app.dependencies.config import get_settings
from app.errors import AppError
from app.services.geofence_engine import GeofenceArea, run_geofence_engine
from app.services.location import save_location_ping
from shared.settings import ApiSettings

router = APIRouter(prefix="/me", tags=["Me"])
logger = logging.getLogger(__name__)


@router.post(
    "/location",
    response_model=MeLocationResponse,
    dependencies=[Depends(require_admin_token)],
)
async def create_me_location(
    payload: MeLocationRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    settings: ApiSettings = Depends(get_settings),
) -> MeLocationResponse:
    """Persist a location ping for the authenticated user."""
    try:
        stored = await save_location_ping(
            db_path=settings.location_db_path,
            latitude=payload.latitude,
            longitude=payload.longitude,
        )
    except (sqlite3.Error, RuntimeError):
        logger.exception("Failed to persist location ping")
        raise AppError(
            status_code=500,
            code="location_persist_failed",
            message="Failed to persist location ping",
        ) from None

    mapping: list[GeofenceArea] = request.app.state.geofence_mapping
    background_tasks.add_task(
        run_geofence_engine,
        settings=settings,
        db_path=settings.location_db_path,
        mapping=mapping,
    )

    return MeLocationResponse(
        success=True,
        id=stored.id,
        timestamp=stored.timestamp,
    )
