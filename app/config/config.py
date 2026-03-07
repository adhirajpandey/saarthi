"""Default configuration values for Saarthi."""

# Base configuration
APP_NAME = "SAARTHI"

# Rate limiting
RATE_LIMIT_DEFAULT = "50/minute"

# Logging configuration
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_FILE = "logs/app.log"

# Geofence templates
GEOFENCE_SUBJECT_TEMPLATE = "Adhiraj Location Update: {area}"
GEOFENCE_EMAIL_TEMPLATE = """Hello Pandey Parivaar,

Adhiraj ki location ka update:

Area - {area}
Update - {trigger}

Regards
Pandey Bot
"""
