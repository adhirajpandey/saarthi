import pytz
from datetime import datetime

# Define the Indian Standard Time timezone
IST = pytz.timezone("Asia/Kolkata")


def get_now_ist() -> datetime:
    """Returns the current datetime localized to IST."""
    # Get current UTC time and convert it to IST
    return datetime.now(IST)


# Note: We will intentionally keep using UTC for JWT 'exp' claims
# as that's the standard (seconds since epoch UTC).
