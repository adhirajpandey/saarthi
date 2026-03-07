from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config.config import APP_NAME
from app.config.settings import load_configuration
from app.api.routers import geofence, health
from shared.config.env import load_environment
from shared.logging import logger
from shared.logging.setup import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize environment, logging and application config."""
    load_environment()
    setup_logging()
    config = load_configuration()
    app.state.config = config
    app.title = config.base.app_name
    logger.info("Application startup complete.")
    yield


app = FastAPI(title=APP_NAME, lifespan=lifespan)

app.include_router(health.router)
app.include_router(geofence.router)


@app.get("/", tags=["Root"])
async def read_root():
    logger.info("Root endpoint '/' called.")
    config = app.state.config
    return {"message": f"Welcome to {config.base.app_name}"}

