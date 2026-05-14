"""Database restore verification CLI."""

import logging
import re
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import TypedDict

import boto3

from shared.logging import setup_logging
from shared.notifications.ntfy import send_ntfy_message
from shared.notifications.whatsapp import send_whatsapp_message
from shared.settings import RestoreDbTestSettings, get_restore_db_test_settings

logger = logging.getLogger(__name__)

TIMESTAMP_RE = re.compile(r"-(\d{10})(?:\.\w+)?$")


class RestoreDbTarget(TypedDict):
    filename: str
    s3_bucket: str
    s3_prefix: str
    test_query: str
    expected_output: str


def build_restore_db_map(settings: RestoreDbTestSettings) -> dict[str, RestoreDbTarget]:
    return {
        "vidwiz": {
            "filename": settings.vidwiz_dump_filename,
            "s3_bucket": settings.backup_bucket,
            "s3_prefix": settings.vidwiz_s3_prefix,
            "test_query": settings.vidwiz_restore_test_query,
            "expected_output": settings.vidwiz_restore_expected_output,
        },
        "trackcrow": {
            "filename": settings.trackcrow_dump_filename,
            "s3_bucket": settings.backup_bucket,
            "s3_prefix": settings.trackcrow_s3_prefix,
            "test_query": settings.trackcrow_restore_test_query,
            "expected_output": settings.trackcrow_restore_expected_output,
        },
        "smashdiary": {
            "filename": settings.smashdiary_dump_filename,
            "s3_bucket": settings.backup_bucket,
            "s3_prefix": settings.smashdiary_s3_prefix,
            "test_query": settings.smashdiary_restore_test_query,
            "expected_output": settings.smashdiary_restore_expected_output,
        },
    }


def latest_key(s3_client, bucket: str, prefix: str) -> str | None:
    """Return the key with the newest epoch in its filename."""
    paginator = s3_client.get_paginator("list_objects_v2")
    latest: tuple[str, int] | None = None
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            match = TIMESTAMP_RE.search(obj["Key"])
            if not match:
                continue
            ts = int(match.group(1))
            if latest is None or ts > latest[1]:
                latest = (obj["Key"], ts)
    return None if latest is None else latest[0]


def download_backup(s3_client, bucket: str, key: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading backup %s from s3://%s/%s", dest.name, bucket, key)
    s3_client.download_file(bucket, key, str(dest))


def create_restore_run_dir(temp_root: Path) -> Path:
    """Create and return a unique disposable directory for one restore test run."""
    run_dir = temp_root / f"{int(time.time())}-{secrets.token_hex(4)}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def wait_ready(container: str, timeout: int) -> None:
    """Poll pg_isready until it succeeds or timeout occurs."""
    logger.info("Waiting for PostgreSQL container %s to become ready", container)
    start = time.time()
    while True:
        try:
            subprocess.run(
                ["docker", "exec", container, "pg_isready", "-U", "postgres"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return
        except subprocess.CalledProcessError:
            if time.time() - start > timeout:
                raise RuntimeError("PostgreSQL did not become ready in time")
            time.sleep(2)


def restore_db(
    db_name: str,
    dump_path: Path,
    settings: RestoreDbTestSettings,
) -> str:
    """Restore a dump into a disposable Postgres container and return its name."""
    container = f"restore-test-{db_name}"
    host_backup_dir = dump_path.parent.resolve()
    subprocess.run(
        ["docker", "rm", "-f", container],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    logger.info("Starting PostgreSQL container %s", container)
    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            container,
            "-e",
            f"POSTGRES_PASSWORD={settings.restore_pg_password}",
            "-e",
            "POSTGRES_USER=postgres",
            "-e",
            f"POSTGRES_DB={db_name}",
            "--mount",
            f"type=bind,src={host_backup_dir},dst=/backups,readonly",
            settings.restore_pg_image,
        ],
        check=True,
    )

    try:
        wait_ready(container, settings.restore_timeout_seconds)
        logger.info("Resetting schema for %s", db_name)
        subprocess.run(
            [
                "docker",
                "exec",
                container,
                "psql",
                "-U",
                "postgres",
                "-d",
                db_name,
                "-c",
                "DROP SCHEMA IF EXISTS public CASCADE;",
            ],
            check=True,
        )
        logger.info("Restoring database %s from %s", db_name, dump_path.name)
        subprocess.run(
            [
                "docker",
                "exec",
                "-i",
                container,
                "psql",
                "-U",
                "postgres",
                "-d",
                db_name,
                "-f",
                f"/backups/{dump_path.name}",
            ],
            check=True,
        )
        return container
    except Exception:
        subprocess.run(
            ["docker", "rm", "-f", container],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        raise


def run_test_query(
    container: str,
    db_name: str,
    test_sql: str,
    expected_output: str,
) -> None:
    logger.info("Running verification query for %s", db_name)
    completed = subprocess.run(
        [
            "docker",
            "exec",
            container,
            "psql",
            "-U",
            "postgres",
            "-d",
            db_name,
            "-t",
            "-A",
            "-c",
            test_sql,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    actual = completed.stdout.strip()
    if expected_output not in actual:
        raise RuntimeError(
            f"Verification failed for {db_name}: expected '{expected_output}', got '{actual}'"
        )
    logger.info("Verification passed for %s", db_name)


def teardown(temp_dir: Path | None, containers: list[str]) -> None:
    """Delete temporary backups and remove restore containers."""
    if temp_dir and temp_dir.exists():
        try:
            shutil.rmtree(temp_dir)
            logger.info("Deleted temporary restore directory %s", temp_dir)
        except Exception as exc:
            logger.warning("Failed to delete %s: %s", temp_dir, exc)

    for container in containers:
        try:
            subprocess.run(
                ["docker", "rm", "-f", container],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info("Removed container %s", container)
        except Exception as exc:
            logger.warning("Failed to remove container %s: %s", container, exc)


def _build_whatsapp_summary(title: str, output_lines: list[str], success: bool) -> str:
    relevant_lines = [
        line for line in output_lines if "Restore verification failed" in line or "Restore verification passed" in line
    ]
    if not relevant_lines:
        relevant_lines = output_lines[-5:]
    status = "SUCCESS" if success else "FAILED"
    return "\n".join([f"{title} ({status})", *relevant_lines[:8]])


def _dispatch_notifications(
    settings: RestoreDbTestSettings,
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
            logger.error("Failed to dispatch ntfy restore notification: %s", exc)

    if settings.whatsapp_enabled:
        try:
            send_whatsapp_message(
                message=_build_whatsapp_summary(title, output_lines, success),
                whatsapp_settings=settings.whatsapp_settings_for_scripts(),
            )
        except Exception as exc:
            logger.error("Failed to dispatch WhatsApp restore notification: %s", exc)


def main() -> int:
    settings: RestoreDbTestSettings | None = None
    output_lines: list[str] = []
    run_dir: Path | None = None
    containers: list[str] = []
    try:
        settings = get_restore_db_test_settings()
        setup_logging(settings.logging_settings())
        db_map = build_restore_db_map(settings)
        temp_root = Path(settings.restore_temp_dir)
        run_dir = create_restore_run_dir(temp_root)
        success = True

        session = boto3.Session(
            aws_access_key_id=settings.aws_access_key,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
        s3_client = session.client("s3")

        try:
            for db_name, db_conf in db_map.items():
                msg = f"\n=== Processing DB: {db_name} ==="
                logger.info(msg.strip())
                output_lines.append(msg)
                container_name = f"restore-test-{db_name}"
                containers.append(container_name)

                try:
                    key = latest_key(s3_client, db_conf["s3_bucket"], db_conf["s3_prefix"])
                    if not key:
                        raise RuntimeError(
                            f"No backup found in s3://{db_conf['s3_bucket']}/{db_conf['s3_prefix']}"
                        )
                    output_lines.append(f"Located backup key: {key}")

                    dump_path = run_dir / db_name / Path(key).name
                    download_backup(s3_client, db_conf["s3_bucket"], key, dump_path)
                    output_lines.append(f"Downloaded backup to {dump_path}")

                    restore_db(db_name, dump_path, settings)
                    output_lines.append("Restore completed")

                    run_test_query(
                        container_name,
                        db_name,
                        db_conf["test_query"],
                        db_conf["expected_output"],
                    )
                    msg = f"Restore verification passed for {db_name}"
                    logger.info(msg)
                    output_lines.append(msg)
                except Exception as exc:
                    success = False
                    msg = f"Restore verification failed for {db_name}: {exc}"
                    logger.error(msg)
                    output_lines.append(msg)
        finally:
            logger.info("=== Teardown ===")
            output_lines.append("\n=== Teardown ===")
            teardown(run_dir, containers)

        if success:
            output_lines.append("All restore verification checks passed")
            title = "DB Restore Verification Success"
        else:
            title = "DB Restore Verification Failed"

        _dispatch_notifications(
            settings=settings,
            title=title,
            output_lines=output_lines,
            success=success,
        )
        return 0 if success else 1
    except Exception as exc:
        setup_logging()
        error_msg = f"Restore verification failed: {exc}"
        logger.exception(error_msg)
        if settings is not None:
            _dispatch_notifications(
                settings=settings,
                title="DB Restore Verification Failed",
                output_lines=[error_msg, *output_lines],
                success=False,
            )
        return 1


if __name__ == "__main__":
    sys.exit(main())
