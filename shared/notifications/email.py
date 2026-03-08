"""SMTP email sender."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from shared.settings import SmtpSettings

logger = logging.getLogger(__name__)


def send_email(
    recipient: str,
    subject: str,
    body: str,
    smtp_settings: SmtpSettings,
    sender_name: str | None = None,
) -> bool:
    """Send an email using SMTP."""
    try:
        message = MIMEMultipart()
        if sender_name:
            message["From"] = f"{sender_name} <{smtp_settings.email}>"
        else:
            message["From"] = smtp_settings.email
        message["To"] = recipient
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL(smtp_settings.host, smtp_settings.port) as server:
            server.login(smtp_settings.email, smtp_settings.app_password)
            server.sendmail(smtp_settings.email, recipient, message.as_string())

        logger.info(f"Email sent successfully to {recipient}")
        return True
    except (smtplib.SMTPException, OSError, TimeoutError) as exc:
        logger.error(f"Failed to send email: {exc}")
        return False
