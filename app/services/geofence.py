"""Geofence notification service."""

from dataclasses import dataclass

from fastapi.concurrency import run_in_threadpool

from shared.notifications.email import send_email
from shared.settings import ApiSettings


@dataclass(slots=True)
class NotificationResult:
    success: bool
    message: str


async def send_geofence_notification(
    settings: ApiSettings,
    area: str,
    event: str,
) -> NotificationResult:
    """Send geofence email notification and return structured outcome."""
    subject = settings.geofence_subject_template.format(area=area)
    body = settings.geofence_email_template.format(area=area, event=event)
    smtp_settings = settings.smtp_settings()

    sent = await run_in_threadpool(
        send_email,
        recipient=settings.geofence_updates_recipient,
        subject=subject,
        body=body,
        smtp_settings=smtp_settings,
        sender_name=settings.geofence_sender_name,
    )

    if not sent:
        return NotificationResult(success=False, message="Failed to send geofence notification email")

    return NotificationResult(success=True, message=f"Geofence notification sent for {area}")
