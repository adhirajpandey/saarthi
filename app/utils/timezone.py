from datetime import datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


def get_now_ist() -> datetime:
    """Returns the current datetime localized to IST."""
    return datetime.now(IST)
