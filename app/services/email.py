"""
Email service using smtplib for sending notifications.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


from app import CONFIG
from app.utils.logging import logger


def send_email(recipient: str, subject: str, body: str, sender_name: str | None = None) -> bool:
    """
    Send an email using SMTP.
    
    Args:
        recipient: Email address of the recipient
        subject: Email subject line
        body: Email body content
        sender_name: Optional display name for the sender
        
    Returns:
        True if email sent successfully, False otherwise
    """
    sender_email = os.getenv("SMTP_EMAIL")
    app_password = os.getenv("SMTP_APP_PASSWORD")
    
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
        
    except smtplib.SMTPException as e:
        logger.error(f"Failed to send email: {e}")
        return False


def send_geofence_notification(area: str, trigger: str) -> bool:
    """
    Send a geofence location update notification email.
    
    Args:
        area: The geofence area name
        trigger: The geofence trigger event
        
    Returns:
        True if email sent successfully, False otherwise
    """
    geofence_config = CONFIG.geofence
    
    if not geofence_config.recipient:
        logger.error("GEOFENCE_UPDATES_RECIPIENT not configured")
        return False
    
    body = geofence_config.email_template.format(area=area, trigger=trigger)
    subject = f"Location Update: {trigger}"
    
    return send_email(
        recipient=geofence_config.recipient,
        subject=subject,
        body=body,
        sender_name=geofence_config.sender_name,
    )
