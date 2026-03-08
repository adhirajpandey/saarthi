"""Google Drive backup CLI."""

import logging
import subprocess

from shared.logging import setup_logging
from shared.notifications.ntfy import send_ntfy_message
from shared.notifications.whatsapp import send_whatsapp_message
from shared.settings import get_backup_gdrive_settings

logger = logging.getLogger(__name__)


def _build_whatsapp_summary(title: str, output_lines: list[str], success: bool) -> str:
    failures = [line for line in output_lines if line.startswith("Failed:")]
    status = "SUCCESS" if success else "FAILED"
    key_lines = failures if failures else output_lines[-5:]
    return "\n".join([f"{title} ({status})", *key_lines[:8]])


def main() -> None:
    settings = get_backup_gdrive_settings()
    setup_logging(settings.logging_settings())
    output_lines: list[str] = []
    success = True

    for folder in settings.gdrive_folders:
        src = f"{settings.gdrive_source}:{folder}"
        dst = f"{settings.gdrive_destination}/{folder}"
        cmd = ["rclone", "copy", src, dst, "--update", "-v", "--drive-shared-with-me"]
        cmd_str = " ".join(cmd)
        logger.info("Running command: %s", cmd_str)
        output_lines.append(f">>> {cmd_str}")

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            if result.stdout:
                logger.info(result.stdout)
                output_lines.append(result.stdout)
            if result.stderr:
                logger.warning(result.stderr)
                output_lines.append(result.stderr)
        except subprocess.CalledProcessError as exc:
            success = False
            error_msg = f"Failed: {exc}"
            logger.error(error_msg)
            output_lines.append(error_msg)
            if exc.stdout:
                output_lines.append(exc.stdout)
            if exc.stderr:
                output_lines.append(exc.stderr)

    if success:
        output_lines.append("Backup completed successfully")
        title = "GDrive Backup Success"
    else:
        title = "GDrive Backup Failed"

    console_output = "\n".join(output_lines)

    if settings.ntfy_enabled:
        try:
            send_ntfy_message(
                message=console_output,
                ntfy_settings=settings.ntfy_settings(),
                title=title,
            )
        except Exception as exc:
            logger.error("Failed to dispatch ntfy backup notification: %s", exc)

    if settings.whatsapp_enabled:
        try:
            send_whatsapp_message(
                message=_build_whatsapp_summary(title, output_lines, success),
                whatsapp_settings=settings.whatsapp_settings_for_scripts(),
            )
        except Exception as exc:
            logger.error("Failed to dispatch WhatsApp backup notification: %s", exc)


if __name__ == "__main__":
    main()
