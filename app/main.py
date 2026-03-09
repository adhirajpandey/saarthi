from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.routers import geofence, health, me
from app.errors import AppError
from app.services.geofence_engine import load_geofence_mapping
from app.services.location import initialize_location_db
from shared.logging import setup_logging
from shared.settings import get_api_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize logging and typed runtime settings."""
    settings = get_api_settings()
    geofence_mapping = load_geofence_mapping(settings.geofence_mapping_path)
    setup_logging(settings.logging_settings())
    initialize_location_db(settings.location_db_path)
    app.state.settings = settings
    app.state.geofence_mapping = geofence_mapping
    app.title = settings.app_name
    logger.info("Application startup complete.")
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI app."""
    app = FastAPI(title="SAARTHI", lifespan=lifespan)

    @app.exception_handler(AppError)
    async def app_error_handler(_, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    app.include_router(health.router)
    app.include_router(geofence.router)
    app.include_router(me.router)

    @app.get("/", tags=["Root"])
    async def read_root():
        logger.info("Root endpoint '/' called.")
        settings = app.state.settings
        return {"message": f"Welcome to {settings.app_name}"}

    return app


app = create_app()
