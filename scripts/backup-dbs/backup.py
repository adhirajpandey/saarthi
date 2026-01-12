import subprocess
import sys
import datetime
import boto3
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

# ----------------------------  Configuration  ---------------------------- #
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")  # IAM user key
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")  # IAM user secret

VIDWIZ_DB_URL = os.getenv("VIDWIZ_DB_URL")
TRACKCROW_DB_URL = os.getenv("TRACKCROW_DB_URL")

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
# ------------------------------------------------------------------------ #


def run_pg_dump(out_file: Path, db_url: str):
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


def sanity_check(dump_file: Path):
    if not dump_file.exists() or dump_file.stat().st_size == 0:
        raise RuntimeError(f"Dump failed: {dump_file} missing or empty")

    print("Sanity check passed")


def upload_to_s3(local_file: Path, bucket: str, prefix: str):
    session = boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )
    s3 = session.client("s3")

    ts = int(datetime.datetime.now().timestamp())
    key = f"{prefix}/{local_file.stem}-{ts}.sql"
    print(f"Uploading to s3://{bucket}/{key}")
    s3.upload_file(str(local_file), bucket, key)


def main():
    for db_name, db_conf in DB_MAP.items():
        print(f"\n=== Processing DB: {db_name} ===")
        dump_path = Path(f"{db_conf['filename']}.sql")
        try:
            run_pg_dump(dump_path, db_conf["url"])
            sanity_check(dump_path)
            upload_to_s3(dump_path, db_conf["s3_bucket"], db_conf["s3_prefix"])
            print(f"Backup complete for {db_name} ✔︎")
        except Exception as exc:
            print(f"Backup failed for {db_name}: {exc}", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("Backup failed:", exc, file=sys.stderr)
        sys.exit(1)