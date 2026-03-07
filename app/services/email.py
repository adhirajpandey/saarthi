"""Application-level email notification service."""

from app import CONFIG
from shared.logging import logger
from shared.notifications.email import send_email


def send_geofence_notification(area: str, trigger: str) -> bool:
    """Send a geofence location update notification email."""
    geofence_config = CONFIG.geofence

    if not geofence_config.recipient:
        logger.error("GEOFENCE_UPDATES_RECIPIENT not configured")
        return False

    body = geofence_config.email_template.format(area=area, trigger=trigger)
    subject = geofence_config.subject_template.format(area=area)

    return send_email(
        recipient=geofence_config.recipient,
        subject=subject,
        body=body,
        sender_name=geofence_config.sender_name,
    )
