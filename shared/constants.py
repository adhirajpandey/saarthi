"""Application-wide constants and defaults."""

# APP
DEFAULT_APP_NAME = "SAARTHI"
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FORMAT = (
    "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
)
DEFAULT_LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_LOG_FILE = "logs/app.log"
DEFAULT_LOCATION_DB_PATH = "data/saarthi.db"
DEFAULT_GEOFENCE_MAPPING_PATH = "data/geofence_mapping.json"

# GLOBAL NOTIFICATION TOGGLES
DEFAULT_EMAIL_ENABLED = True
DEFAULT_NTFY_ENABLED = True
DEFAULT_WHATSAPP_ENABLED = True

# WHATSAPP NOTIFICATIONS
DEFAULT_WHATSAPP_TIMEOUT_SECONDS = 20
