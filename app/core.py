from slowapi import Limiter
from slowapi.util import get_remote_address
from logging import info, getLogger

logger = getLogger(__name__)
info("Logger initialized properly.")

limiter = Limiter(key_func=get_remote_address)
info("Rate limiter initialized.")
