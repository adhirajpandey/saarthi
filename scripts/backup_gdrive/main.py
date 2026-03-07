"""Google Drive backup CLI."""

import subprocess

from shared.config.env import load_environment
from shared.logging.setup import setup_logging
from shared.notifications.ntfy import send_ntfy_message

load_environment()

SRC = "personal-drive"
DST = "dwaar-s3:dwaar/backups/gdrive"

FOLDERS = [
    "[01] PERSONAL",
    "[02] PROFESSIONAL",
]


def main() -> None:
    setup_logging()
    output_lines = []
    success = True

    for folder in FOLDERS:
        src = f"{SRC}:{folder}"
        dst = f"{DST}/{folder}"
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
        topic="notifs",
        message=console_output,
        title=title,
    )


if __name__ == "__main__":
    main()
