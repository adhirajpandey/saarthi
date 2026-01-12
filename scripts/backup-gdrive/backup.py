# only run this script on raspi as it needs already configured rclone
import subprocess

SRC = "personal-drive"
DST = "dwaar-s3:dwaar/backups/gdrive"

FOLDERS = [
    "[01] PERSONAL",
    "[02] PROFESSIONAL",
]

def main():
    for folder in FOLDERS:
        src = f"{SRC}:{folder}"
        dst = f"{DST}/{folder}"
        cmd = ["rclone", "copy", src, dst, "--update", "--progress", "--drive-shared-with-me"]
        print(">>>", " ".join(cmd))
        subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()