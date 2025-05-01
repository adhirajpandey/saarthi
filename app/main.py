from fastapi import FastAPI

from .config import CONFIG
from .routers import health, login, chat
from .core import logger

app = FastAPI(title=CONFIG.base.app_name)

app.include_router(health.router)
app.include_router(login.router)
app.include_router(chat.router)


@app.get("/", tags=["Root"])
async def read_root():
    logger.info("Root endpoint '/' called.")
    return {"message": f"Welcome to {CONFIG.base.app_name}"}


# uv run uvicorn app.main:app --log-config log_conf.yml --reload --host 0.0.0.0 --port 8000
