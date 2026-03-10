"""Local Saarthi config (copy to `config.py`, which is gitignored).

Use this for non-secret values that do not need to be in `.env`.
Secrets should remain in environment variables.
"""

APP_CONFIG = {
    "APP_NAME": "SAARTHI",
    "LOCATION_DB_PATH": "data/saarthi_location.db",
    "GEOFENCE_MAPPING_PATH": "data/geofence_mapping.json",
}

LOGGING_CONFIG = {
    "LOG_LEVEL": "INFO",
    "LOG_FORMAT": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "LOG_DATE_FORMAT": "%Y-%m-%d %H:%M:%S",
    "LOG_FILE": "logs/saarthi.log",
}

CHANNEL_CONFIG = {
    "EMAIL_ENABLED": True,
    "NTFY_ENABLED": True,
    "WHATSAPP_ENABLED": True,
}

WHATSAPP_CONFIG = {
    "WHATSAPP_SSH_HOST": "adhiraj@100.88.141.119",
    "WHATSAPP_REMOTE_SCRIPT_PATH": "/home/adhiraj/send_whatsapp.sh",
    "WHATSAPP_TARGET_FAMILY": "120363369409471870@g.us",
    "WHATSAPP_TARGET_PERSONAL": "+918791335061",
    "WHATSAPP_TIMEOUT_SECONDS": 30,
}

GEOFENCE_CONFIG = {
    "GEOFENCE_UPDATES_RECIPIENT": "updates@example.com",
    "GEOFENCE_SENDER_NAME": "Saarthi",
    "GEOFENCE_SUBJECT_TEMPLATE": "Saarthi update: {area} ({event})",
    "GEOFENCE_EMAIL_TEMPLATE": "Area={area}, Event={event}",
    "GEOFENCE_WHATSAPP_TEMPLATE": "Area={area}, Event={event}",
    "SMTP_EMAIL": "smtp@example.com",
    "SMTP_HOST": "smtp.example.com",
    "SMTP_PORT": 587,
}

BACKUP_CONFIG = {
    "BACKUP_BUCKET": "my-backup-bucket",
    "VIDWIZ_S3_PREFIX": "db-backups/vidwiz",
    "TRACKCROW_S3_PREFIX": "db-backups/trackcrow",
    "VIDWIZ_DUMP_FILENAME": "vidwiz.sql.gz",
    "TRACKCROW_DUMP_FILENAME": "trackcrow.sql.gz",
}

GDRIVE_CONFIG = {
    "GDRIVE_SOURCE": "dwaar-s3:dwaar/backups/gdrive",
    "GDRIVE_DESTINATION": "s3://my-backups/gdrive",
    "GDRIVE_FOLDERS": ["Photos", "Documents"],
}

NTFY_CONFIG = {
    "NTFY_BASE_URL": "https://ntfy.sh",
    "NTFY_TOPIC": "saarthi-backups",
}

# Final merged view consumed by Saarthi runtime.
CONFIG = {
    **APP_CONFIG,
    **LOGGING_CONFIG,
    **CHANNEL_CONFIG,
    **WHATSAPP_CONFIG,
    **GEOFENCE_CONFIG,
    **BACKUP_CONFIG,
    **GDRIVE_CONFIG,
    **NTFY_CONFIG,
}
