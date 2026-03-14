"""Database backup CLI."""

import datetime
import logging
import subprocess
import sys
from pathlib import Path
from typing import TypedDict

import boto3

from shared.logging import setup_logging
from shared.notifications.ntfy import send_ntfy_message
from shared.notifications.whatsapp import send_whatsapp_message
from shared.settings import BackupDbSettings, get_backup_db_settings

logger = logging.getLogger(__name__)


class DbBackupTarget(TypedDict):
    url: str
    filename: str
    s3_bucket: str
    s3_prefix: str


def build_db_map(settings: BackupDbSettings) -> dict[str, DbBackupTarget]:
    return {
        "vidwiz": {
            "url": settings.vidwiz_db_url,
            "filename": settings.vidwiz_dump_filename,
            "s3_bucket": settings.backup_bucket,
            "s3_prefix": settings.vidwiz_s3_prefix,
        },
        "trackcrow": {
            "url": settings.trackcrow_db_url,
            "filename": settings.trackcrow_dump_filename,
            "s3_bucket": settings.backup_bucket,
            "s3_prefix": settings.trackcrow_s3_prefix,
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
    logger.info("Running pg_dump for %s", out_file)
    subprocess.run(cmd, check=True)


def sanity_check(dump_file: Path) -> None:
    if not dump_file.exists() or dump_file.stat().st_size == 0:
        raise RuntimeError(f"Dump failed: {dump_file} missing or empty")

    logger.info("Sanity check passed for %s", dump_file)


def upload_to_s3(
    local_file: Path,
    bucket: str,
    prefix: str,
    settings: BackupDbSettings,
) -> None:
    session = boto3.Session(
        aws_access_key_id=settings.aws_access_key,
        aws_secret_access_key=settings.aws_secret_access_key,
    )
    s3 = session.client("s3")

    ts = int(datetime.datetime.now().timestamp())
    key = f"{prefix}/{local_file.stem}-{ts}.sql"
    logger.info("Uploading %s to s3://%s/%s", local_file, bucket, key)
    s3.upload_file(str(local_file), bucket, key)


def teardown(files_to_cleanup: list[Path]) -> None:
    """Remove any dump files created during execution."""
    for file_path in files_to_cleanup:
        try:
            if file_path.exists():
                file_path.unlink()
                logger.info("Cleaned up temporary file %s", file_path)
        except Exception as exc:
            logger.warning("Failed to clean up %s: %s", file_path, exc)


def _build_whatsapp_summary(title: str, output_lines: list[str], success: bool) -> str:
    relevant_lines = [
        line for line in output_lines if "Backup failed" in line or "Backup complete" in line
    ]
    if not relevant_lines:
        relevant_lines = output_lines[-5:]
    status = "SUCCESS" if success else "FAILED"
    return "\n".join([f"{title} ({status})", *relevant_lines[:8]])


def _dispatch_notifications(
    settings: BackupDbSettings,
    title: str,
    output_lines: list[str],
    success: bool,
) -> None:
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
            summary = _build_whatsapp_summary(title, output_lines, success)
            send_whatsapp_message(
                message=summary,
                whatsapp_settings=settings.whatsapp_settings_for_scripts(),
            )
        except Exception as exc:
            logger.error("Failed to dispatch WhatsApp backup notification: %s", exc)


def main() -> int:
    settings: BackupDbSettings | None = None
    output_lines: list[str] = []
    try:
        settings = get_backup_db_settings()
        setup_logging(settings.logging_settings())
        db_map = build_db_map(settings)

        created_files: list[Path] = []
        success = True

        try:
            for db_name, db_conf in db_map.items():
                msg = f"\n=== Processing DB: {db_name} ==="
                logger.info(msg.strip())
                output_lines.append(msg)

                dump_path = Path(f"{db_conf['filename']}.sql")
                created_files.append(dump_path)
                try:
                    run_pg_dump(dump_path, db_conf["url"])
                    output_lines.append("Running pg_dump command...")

                    sanity_check(dump_path)
                    output_lines.append("Sanity check passed")

                    upload_to_s3(
                        local_file=dump_path,
                        bucket=db_conf["s3_bucket"],
                        prefix=db_conf["s3_prefix"],
                        settings=settings,
                    )
                    output_lines.append(
                        f"Uploading to s3://{db_conf['s3_bucket']}/{db_conf['s3_prefix']}/..."
                    )

                    msg = f"Backup complete for {db_name}"
                    logger.info(msg)
                    output_lines.append(msg)
                except Exception as exc:
                    success = False
                    msg = f"Backup failed for {db_name}: {exc}"
                    logger.error(msg)
                    output_lines.append(msg)
        finally:
            logger.info("=== Teardown ===")
            output_lines.append("\n=== Teardown ===")
            teardown(created_files)

        if success:
            output_lines.append("All backups completed successfully")
            title = "DB Backup Success"
        else:
            title = "DB Backup Failed"

        _dispatch_notifications(
            settings=settings,
            title=title,
            output_lines=output_lines,
            success=success,
        )
        return 0 if success else 1
    except Exception as exc:
        setup_logging()
        error_msg = f"Backup failed: {exc}"
        logger.exception(error_msg)
        if settings is not None:
            _dispatch_notifications(
                settings=settings,
                title="DB Backup Failed",
                output_lines=[error_msg, *output_lines],
                success=False,
            )
        return 1


if __name__ == "__main__":
    sys.exit(main())
