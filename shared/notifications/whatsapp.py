"""WhatsApp notification sender over SSH."""

import logging
import subprocess

from shared.settings import WhatsAppSettings

logger = logging.getLogger(__name__)


def send_whatsapp_message(
    message: str,
    whatsapp_settings: WhatsAppSettings,
) -> bool:
    """Send a WhatsApp message by running a remote script via SSH."""
    command = [
        "ssh",
        whatsapp_settings.ssh_host,
        "python3",
        whatsapp_settings.remote_script_path,
        "--message",
        message,
        "--target",
        whatsapp_settings.target,
    ]

    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=whatsapp_settings.timeout_seconds,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.error("Failed to send WhatsApp message: %s", exc)
        return False

    if result.returncode == 0:
        logger.info("WhatsApp message sent successfully")
        return True

    logger.error(
        "WhatsApp sender returned non-zero exit code %s (stdout=%s, stderr=%s)",
        result.returncode,
        result.stdout.strip(),
        result.stderr.strip(),
    )
    return False
