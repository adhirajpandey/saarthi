"""SMTP email sender."""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from shared.config.env import get_env, load_environment
from shared.logging import logger


def send_email(recipient: str, subject: str, body: str, sender_name: str | None = None) -> bool:
    """Send an email using SMTP."""
    load_environment()
    sender_email = get_env("SMTP_EMAIL")
    app_password = get_env("SMTP_APP_PASSWORD")

    if not sender_email or not app_password:
        logger.error("SMTP_EMAIL or SMTP_APP_PASSWORD not configured")
        return False

    try:
        message = MIMEMultipart()
        if sender_name:
            message["From"] = f"{sender_name} <{sender_email}>"
        else:
            message["From"] = sender_email
        message["To"] = recipient
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, app_password)
            server.sendmail(sender_email, recipient, message.as_string())

        logger.info(f"Email sent successfully to {recipient}")
        return True
    except smtplib.SMTPException as exc:
        logger.error(f"Failed to send email: {exc}")
        return False

