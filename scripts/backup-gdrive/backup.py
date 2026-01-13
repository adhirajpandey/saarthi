# only run this script on raspi as it needs already configured rclone
import subprocess
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.utils.ntfy import send_ntfy_message

SRC = "personal-drive"
DST = "dwaar-s3:dwaar/backups/gdrive"

FOLDERS = [
    "[01] PERSONAL",
    "[02] PROFESSIONAL",
]

def main():
    output_lines = []
    success = True
    
    for folder in FOLDERS:
        src = f"{SRC}:{folder}"
        dst = f"{DST}/{folder}"
        cmd = ["rclone", "copy", src, dst, "--update", "--progress", "--drive-shared-with-me"]
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
        except subprocess.CalledProcessError as e:
            success = False
            error_msg = f"❌ Failed: {e}"
            print(error_msg)
            output_lines.append(error_msg)
            if e.stdout:
                output_lines.append(e.stdout)
            if e.stderr:
                output_lines.append(e.stderr)
    
    if success:
        output_lines.append("✅ Backup completed successfully")
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