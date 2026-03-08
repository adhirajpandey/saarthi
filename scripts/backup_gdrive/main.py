"""Google Drive backup CLI."""

import subprocess

from shared.logging.setup import setup_logging
from shared.notifications.ntfy import send_ntfy_message
from shared.settings import get_backup_gdrive_settings


def main() -> None:
    settings = get_backup_gdrive_settings()
    setup_logging(settings.logging_settings())
    output_lines = []
    success = True

    for folder in settings.gdrive_folders:
        src = f"{settings.gdrive_source}:{folder}"
        dst = f"{settings.gdrive_destination}/{folder}"
        cmd = ["rclone", "copy", src, dst, "--update", "-v", "--drive-shared-with-me"]
        cmd_str = " ".join(cmd)
        print(">>>", cmd_str)
        output_lines.append(f">>> {cmd_str}")

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            if result.stdout:
                print(result.stdout)
                output_lines.append(result.stdout)
            if result.stderr:
                print(result.stderr)
                output_lines.append(result.stderr)
        except subprocess.CalledProcessError as exc:
            success = False
            error_msg = f"Failed: {exc}"
            print(error_msg)
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

    send_ntfy_message(
        message=console_output,
        ntfy_settings=settings.ntfy_settings(),
        title=title,
    )


if __name__ == "__main__":
    main()
