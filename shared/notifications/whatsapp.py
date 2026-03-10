"""WhatsApp notification sender over SSH."""

import logging
import shlex
import subprocess

from shared.settings import WhatsAppSettings

logger = logging.getLogger(__name__)


def send_whatsapp_message(
    message: str,
    whatsapp_settings: WhatsAppSettings,
) -> bool:
    """Send a WhatsApp message by running a remote script via SSH."""
    remote_command = " ".join(
        [
            "python3",
            shlex.quote(whatsapp_settings.remote_script_path),
            "--message",
            shlex.quote(message),
            "--target",
            shlex.quote(whatsapp_settings.target),
        ]
    )
    command = [
        "ssh",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        whatsapp_settings.ssh_host,
        remote_command,
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

    if result.returncode == 255:
        logger.error(
            "WhatsApp SSH transport failed with exit code 255 (stdout=%s, stderr=%s)",
            result.stdout.strip(),
            result.stderr.strip(),
        )
    else:
        logger.error(
            "WhatsApp sender returned non-zero exit code %s (stdout=%s, stderr=%s)",
            result.returncode,
            result.stdout.strip(),
            result.stderr.strip(),
        )
    return False
