"""Application-wide constants and defaults."""

# APP
DEFAULT_APP_NAME = "SAARTHI"
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FORMAT = (
    "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
)
DEFAULT_LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_LOG_FILE = "logs/app.log"

# GLOBAL NOTIFICATION TOGGLES
DEFAULT_EMAIL_ENABLED = True
DEFAULT_NTFY_ENABLED = True
DEFAULT_WHATSAPP_ENABLED = False

# WHATSAPP NOTIFICATIONS
DEFAULT_WHATSAPP_TIMEOUT_SECONDS = 20

# GEOFENCE EMAIL
DEFAULT_SMTP_HOST = "smtp.gmail.com"
DEFAULT_SMTP_PORT = 465

DEFAULT_GEOFENCE_SUBJECT_TEMPLATE = "Adhiraj Location Update: {area}"
DEFAULT_GEOFENCE_EMAIL_TEMPLATE = """Hello Pandey Parivaar,

Adhiraj ki location ka update:

Area - {area}
Update - {event}

Regards
Pandey Bot
"""
DEFAULT_GEOFENCE_WHATSAPP_TEMPLATE = "Adhiraj location update: Area={area}, Event={event}"

# NTFY NOTIFICATIONS
DEFAULT_NTFY_TOPIC = "notifs"

# DATABASE BACKUP SCRIPT
DEFAULT_BACKUP_BUCKET = "dwaar"
DEFAULT_VIDWIZ_S3_PREFIX = "backups/db/vidwiz"
DEFAULT_TRACKCROW_S3_PREFIX = "backups/db/trackcrow"
DEFAULT_VIDWIZ_DUMP_FILENAME = "vidwiz-dump"
DEFAULT_TRACKCROW_DUMP_FILENAME = "trackcrow-dump"

# GDRIVE BACKUP SCRIPT (OPTIONAL OVERRIDES)
DEFAULT_GDRIVE_SOURCE = "personal-drive"
DEFAULT_GDRIVE_DESTINATION = "dwaar-s3:dwaar/backups/gdrive"
DEFAULT_GDRIVE_FOLDERS = ["[01] PERSONAL", "[02] PROFESSIONAL"]
