from fastapi import FastAPI

from app import CONFIG
from .routers import health, login, chat
from .utils.logging import logger

app = FastAPI(title=CONFIG.base.app_name)

app.include_router(health.router)
app.include_router(login.router)
app.include_router(chat.router)


@app.get("/", tags=["Root"])
async def read_root():
    logger.info("Root endpoint '/' called.")
    return {"message": f"Welcome to {CONFIG.base.app_name}"}

