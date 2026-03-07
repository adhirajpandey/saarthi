"""Database backup CLI."""

import datetime
import subprocess
import sys
from pathlib import Path

import boto3

from shared.config.env import get_env, load_environment
from shared.notifications.ntfy import send_ntfy_message

load_environment()

AWS_ACCESS_KEY = get_env("AWS_ACCESS_KEY")
AWS_SECRET_ACCESS_KEY = get_env("AWS_SECRET_ACCESS_KEY")
VIDWIZ_DB_URL = get_env("VIDWIZ_DB_URL")
TRACKCROW_DB_URL = get_env("TRACKCROW_DB_URL")

if not AWS_ACCESS_KEY or not AWS_SECRET_ACCESS_KEY:
    raise ValueError("AWS_ACCESS_KEY and AWS_SECRET_ACCESS_KEY must be set")

if not VIDWIZ_DB_URL or not TRACKCROW_DB_URL:
    raise ValueError("VIDWIZ_DB_URL and TRACKCROW_DB_URL must be set")

DB_MAP = {
    "vidwiz": {
        "url": VIDWIZ_DB_URL,
        "filename": "vidwiz-dump",
        "s3_bucket": "dwaar",
        "s3_prefix": "backups/db/vidwiz",
    },
    "trackcrow": {
        "url": TRACKCROW_DB_URL,
        "filename": "trackcrow-dump",
        "s3_bucket": "dwaar",
        "s3_prefix": "backups/db/trackcrow",
    },
}


def run_pg_dump(out_file: Path, db_url: str) -> None:
    cmd = [
        "pg_dump",
        f"--dbname={db_url}",
        "--schema=public",
        "--no-owner",
        "--no-privileges",
        f"--file={out_file}",
    ]
    print("Running pg_dump command...")
    subprocess.run(cmd, check=True)


def sanity_check(dump_file: Path) -> None:
    if not dump_file.exists() or dump_file.stat().st_size == 0:
        raise RuntimeError(f"Dump failed: {dump_file} missing or empty")

    print("Sanity check passed")


def upload_to_s3(local_file: Path, bucket: str, prefix: str) -> None:
    session = boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )
    s3 = session.client("s3")

    ts = int(datetime.datetime.now().timestamp())
    key = f"{prefix}/{local_file.stem}-{ts}.sql"
    print(f"Uploading to s3://{bucket}/{key}")
    s3.upload_file(str(local_file), bucket, key)


def teardown(files_to_cleanup: list[Path]) -> None:
    """Remove any dump files created during execution."""
    for file_path in files_to_cleanup:
        try:
            if file_path.exists():
                file_path.unlink()
                print(f"Cleaned up: {file_path}")
        except Exception as exc:
            print(f"Warning: Failed to clean up {file_path}: {exc}", file=sys.stderr)


def main() -> None:
    created_files: list[Path] = []
    output_lines = []
    success = True

    try:
        for db_name, db_conf in DB_MAP.items():
            msg = f"\n=== Processing DB: {db_name} ==="
            print(msg)
            output_lines.append(msg)

            dump_path = Path(f"{db_conf['filename']}.sql")
            created_files.append(dump_path)
            try:
                run_pg_dump(dump_path, db_conf["url"])
                output_lines.append("Running pg_dump command...")

                sanity_check(dump_path)
                output_lines.append("Sanity check passed")

                upload_to_s3(dump_path, db_conf["s3_bucket"], db_conf["s3_prefix"])
                output_lines.append(
                    f"Uploading to s3://{db_conf['s3_bucket']}/{db_conf['s3_prefix']}/..."
                )

                msg = f"Backup complete for {db_name}"
                print(msg)
                output_lines.append(msg)
            except Exception as exc:
                success = False
                msg = f"Backup failed for {db_name}: {exc}"
                print(msg, file=sys.stderr)
                output_lines.append(msg)
    finally:
        print("\n=== Teardown ===")
        output_lines.append("\n=== Teardown ===")
        teardown(created_files)

    if success:
        output_lines.append("All backups completed successfully")
        title = "DB Backup Success"
    else:
        title = "DB Backup Failed"

    console_output = "\n".join(output_lines)

    send_ntfy_message(
        topic="notifs",
        message=console_output,
        title=title,
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        error_msg = f"Backup failed: {exc}"
        print(error_msg, file=sys.stderr)
        send_ntfy_message(
            topic="notifs",
            message=error_msg,
            title="DB Backup Failed",
        )
        sys.exit(1)

