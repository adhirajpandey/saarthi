"""Tests for script configuration behavior."""

import copy
import contextlib
import io
import re
import subprocess
from pathlib import Path
import runpy

from scripts.cloudflare_dns import main as cloudflare_dns_main
from scripts.cloudflare_zones import main as cloudflare_zones_main
from scripts.google_tasks_auth import main as google_tasks_auth_main
from scripts.backup_dbs import main as backup_dbs_main
from scripts.backup_gdrive import main as backup_gdrive_main
from scripts.restore_dbs_test import main as restore_dbs_test_main
from scripts.backup_dbs.main import _dispatch_notifications, build_db_map
from scripts.backup_gdrive.main import _build_whatsapp_summary
from scripts.restore_dbs_test.main import (
    _dispatch_notifications as dispatch_restore_notifications,
)
from scripts.restore_dbs_test.main import (
    _build_whatsapp_summary as build_restore_whatsapp_summary,
)
from scripts.restore_dbs_test.main import (
    build_restore_db_map,
    create_restore_run_dir,
    latest_key,
    restore_db,
)
from scripts.schedule_scripts import main as schedule_main
from scripts.schedule_scripts.main import generate_files
from shared.logging.setup import setup_logging
from shared.settings import (
    BackupDbSettings,
    BackupGdriveSettings,
    RestoreDbTestSettings,
    SchedulerSettings,
)

_EXAMPLE_CONFIG_PATH = Path(__file__).resolve().parents[1] / "app" / "config" / "config.example.py"
_BASE_CONFIG = runpy.run_path(str(_EXAMPLE_CONFIG_PATH))["CONFIG"]
_HERMES_BIN = "/home/pookie/.local/bin/hermes"
_HERMES_DM_TARGET = "whatsapp:166601898885178@lid"


def _runtime_kwargs(**overrides):
    cfg = copy.deepcopy(_BASE_CONFIG)
    data = {
        "log_level": cfg["LOG_LEVEL"],
        "log_format": cfg["LOG_FORMAT"],
        "log_date_format": cfg["LOG_DATE_FORMAT"],
        "log_file": cfg["LOG_FILE"],
        "email_enabled": cfg["EMAIL_ENABLED"],
        "ntfy_enabled": cfg["NTFY_ENABLED"],
        "whatsapp_enabled": cfg["WHATSAPP_ENABLED"],
        "whatsapp_ssh_host": cfg["WHATSAPP_SSH_HOST"],
        "whatsapp_remote_script_path": cfg["WHATSAPP_REMOTE_SCRIPT_PATH"],
        "whatsapp_target_family": cfg["WHATSAPP_TARGET_FAMILY"],
        "whatsapp_target_personal": cfg["WHATSAPP_TARGET_PERSONAL"],
        "whatsapp_timeout_seconds": cfg["WHATSAPP_TIMEOUT_SECONDS"],
        "ntfy_topic": cfg["NTFY_TOPIC"],
    }
    data.update(overrides)
    return data


def _backup_db_settings(**overrides) -> BackupDbSettings:
    defaults = {
        "ntfy_enabled": False,
        "whatsapp_enabled": True,
        "whatsapp_ssh_host": "pookie",
        "whatsapp_remote_script_path": _HERMES_BIN,
        "whatsapp_target_personal": _HERMES_DM_TARGET,
        "backup_bucket": "my-bucket",
        "vidwiz_s3_prefix": "db/vidwiz",
        "trackcrow_s3_prefix": "db/trackcrow",
        "smashdiary_s3_prefix": "db/smashdiary",
        "vidwiz_dump_filename": "vidwiz-custom",
        "trackcrow_dump_filename": "trackcrow-custom",
        "smashdiary_dump_filename": "smashdiary-custom",
    }
    defaults.update(overrides)
    return BackupDbSettings(
        **_runtime_kwargs(**defaults),
        aws_access_key="ak",
        aws_secret_access_key="sk",
        vidwiz_db_url="postgres://vidwiz",
        trackcrow_db_url="postgres://trackcrow",
        smashdiary_db_url="postgres://smashdiary",
    )


def _backup_gdrive_settings(**overrides) -> BackupGdriveSettings:
    defaults = {
        "ntfy_enabled": False,
        "whatsapp_enabled": True,
        "whatsapp_ssh_host": "pookie",
        "whatsapp_remote_script_path": _HERMES_BIN,
        "whatsapp_target_personal": _HERMES_DM_TARGET,
    }
    defaults.update(overrides)
    return BackupGdriveSettings(
        **_runtime_kwargs(**defaults),
        gdrive_source="personal-drive",
        gdrive_destination="dwaar-s3:dwaar/backups/gdrive",
        gdrive_folders=["folder-1"],
    )


def _restore_db_test_settings(**overrides) -> RestoreDbTestSettings:
    defaults = {
        "ntfy_enabled": False,
        "whatsapp_enabled": True,
        "whatsapp_ssh_host": "pookie",
        "whatsapp_remote_script_path": _HERMES_BIN,
        "whatsapp_target_personal": _HERMES_DM_TARGET,
        "backup_bucket": "my-bucket",
        "vidwiz_s3_prefix": "db/vidwiz",
        "trackcrow_s3_prefix": "db/trackcrow",
        "smashdiary_s3_prefix": "db/smashdiary",
        "vidwiz_dump_filename": "vidwiz-custom",
        "trackcrow_dump_filename": "trackcrow-custom",
        "smashdiary_dump_filename": "smashdiary-custom",
        "restore_pg_image": "postgres:15",
        "restore_pg_password": "postgres",
        "restore_timeout_seconds": 60,
        "restore_temp_dir": "data/restore-db-tests",
        "vidwiz_restore_test_query": "SELECT * FROM videos",
        "vidwiz_restore_expected_output": "video-result",
        "trackcrow_restore_test_query": 'SELECT * FROM "Transaction"',
        "trackcrow_restore_expected_output": "store-result",
        "smashdiary_restore_test_query": "SELECT 1",
        "smashdiary_restore_expected_output": "1",
    }
    defaults.update(overrides)
    return RestoreDbTestSettings(
        **_runtime_kwargs(**defaults),
        aws_access_key="ak",
        aws_secret_access_key="sk",
    )


def test_build_db_map_uses_settings_values() -> None:
    settings = BackupDbSettings(
        **_runtime_kwargs(),
        aws_access_key="ak",
        aws_secret_access_key="sk",
        vidwiz_db_url="postgres://vidwiz",
        trackcrow_db_url="postgres://trackcrow",
        smashdiary_db_url="postgres://smashdiary",
        ntfy_base_url="https://ntfy.example.com",
        ntfy_token="token",
        backup_bucket="my-bucket",
        vidwiz_s3_prefix="db/vidwiz",
        trackcrow_s3_prefix="db/trackcrow",
        smashdiary_s3_prefix="db/smashdiary",
        vidwiz_dump_filename="vidwiz-custom",
        trackcrow_dump_filename="trackcrow-custom",
        smashdiary_dump_filename="smashdiary-custom",
    )

    db_map = build_db_map(settings)

    assert db_map["vidwiz"]["s3_bucket"] == "my-bucket"
    assert db_map["vidwiz"]["s3_prefix"] == "db/vidwiz"
    assert db_map["vidwiz"]["filename"] == "vidwiz-custom"
    assert db_map["trackcrow"]["s3_prefix"] == "db/trackcrow"
    assert db_map["trackcrow"]["filename"] == "trackcrow-custom"
    assert db_map["smashdiary"]["s3_prefix"] == "db/smashdiary"
    assert db_map["smashdiary"]["filename"] == "smashdiary-custom"


def test_cloudflare_zones_main_prints_json(monkeypatch, runtime_config) -> None:
    runtime_config()
    monkeypatch.setattr("scripts.cloudflare_zones.main.setup_logging", lambda *_: None)
    monkeypatch.setattr(
        "scripts.cloudflare_zones.main.list_zones",
        lambda **_kwargs: {
            "success": True,
            "count": 1,
            "filters": {"page": 1, "per_page": 20},
            "zones": [{"id": "zone-1", "name": "example.com"}],
        },
    )
    monkeypatch.setattr("sys.argv", ["cloudflare-zones", "list", "--json"])

    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        result = cloudflare_zones_main.main()

    assert result == 0
    assert '"name": "example.com"' in stdout.getvalue()


def test_cloudflare_dns_main_returns_1_on_validation_error(monkeypatch, runtime_config) -> None:
    runtime_config()
    monkeypatch.setattr("scripts.cloudflare_dns.main.setup_logging", lambda *_: None)
    monkeypatch.setattr("sys.argv", ["cloudflare-dns", "list", "--zone-id", "z1", "--zone-name", "example.com"])

    stderr = io.StringIO()
    with contextlib.redirect_stderr(stderr):
        result = cloudflare_dns_main.main()

    assert result == 1
    assert "exactly one of zone_id or zone_name" in stderr.getvalue()


def test_google_tasks_auth_main_prints_success_message(
    monkeypatch, runtime_config, test_workspace: Path
) -> None:
    runtime_config()
    token_path = test_workspace / "google-token.json"
    monkeypatch.setenv("GOOGLE_TASKS_TOKEN_PATH", str(token_path))
    monkeypatch.setattr("scripts.google_tasks_auth.main.setup_logging", lambda *_: None)
    monkeypatch.setattr(
        "scripts.google_tasks_auth.main.run_google_tasks_oauth_bootstrap",
        lambda **_kwargs: token_path,
    )
    monkeypatch.setattr("sys.argv", ["google-tasks-auth"])

    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        result = google_tasks_auth_main.main()

    assert result == 0
    assert str(token_path) in stdout.getvalue()


def test_google_tasks_auth_main_returns_1_on_failure(monkeypatch, runtime_config) -> None:
    runtime_config()
    monkeypatch.setattr("scripts.google_tasks_auth.main.setup_logging", lambda *_: None)
    monkeypatch.setattr(
        "scripts.google_tasks_auth.main.run_google_tasks_oauth_bootstrap",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    monkeypatch.setattr("sys.argv", ["google-tasks-auth"])

    stderr = io.StringIO()
    with contextlib.redirect_stderr(stderr):
        result = google_tasks_auth_main.main()

    assert result == 1
    assert "Failed to authorize Google Tasks" in stderr.getvalue()


def test_google_tasks_auth_main_supports_headless_flag(monkeypatch, runtime_config) -> None:
    runtime_config()
    monkeypatch.setattr("scripts.google_tasks_auth.main.setup_logging", lambda *_: None)
    monkeypatch.setattr(
        "scripts.google_tasks_auth.main.run_google_tasks_oauth_bootstrap",
        lambda **kwargs: kwargs["settings"].token_path() if kwargs["headless"] else None,
    )
    monkeypatch.setattr("sys.argv", ["google-tasks-auth", "--headless"])

    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        result = google_tasks_auth_main.main()

    assert result == 0


def test_build_restore_db_map_uses_inherited_and_restore_values() -> None:
    settings = _restore_db_test_settings()

    db_map = build_restore_db_map(settings)

    assert db_map["vidwiz"]["s3_bucket"] == "my-bucket"
    assert db_map["vidwiz"]["filename"] == "vidwiz-custom"
    assert db_map["vidwiz"]["test_query"] == "SELECT * FROM videos"
    assert db_map["trackcrow"]["s3_prefix"] == "db/trackcrow"
    assert db_map["trackcrow"]["expected_output"] == "store-result"
    assert db_map["smashdiary"]["s3_prefix"] == "db/smashdiary"
    assert db_map["smashdiary"]["expected_output"] == "1"


def test_latest_key_prefers_newest_timestamp() -> None:
    class FakePaginator:
        def paginate(self, **_kwargs):
            return [
                {"Contents": [{"Key": "db/vidwiz/vidwiz-custom-1710000000.sql"}]},
                {
                    "Contents": [
                        {"Key": "db/vidwiz/vidwiz-custom-1710000020.sql"},
                        {"Key": "db/vidwiz/not-a-backup.txt"},
                    ]
                },
            ]

    class FakeS3Client:
        def get_paginator(self, name: str):
            assert name == "list_objects_v2"
            return FakePaginator()

    assert latest_key(FakeS3Client(), "my-bucket", "db/vidwiz") == "db/vidwiz/vidwiz-custom-1710000020.sql"


def test_create_restore_run_dir_creates_unique_child_under_temp_root(
    monkeypatch, test_workspace: Path
) -> None:
    temp_root = test_workspace / "data" / "restore-db-tests"
    monkeypatch.setattr("scripts.restore_dbs_test.main.time.time", lambda: 1715660000)
    monkeypatch.setattr("scripts.restore_dbs_test.main.secrets.token_hex", lambda _n: "deadbeef")

    run_dir = create_restore_run_dir(temp_root)

    assert run_dir == temp_root / "1715660000-deadbeef"
    assert run_dir.is_dir()
    assert run_dir.parent == temp_root
    assert re.fullmatch(r"\d{10}-[0-9a-f]{8}", run_dir.name)


def test_restore_db_uses_absolute_readonly_bind_mount_for_relative_temp_dir(
    monkeypatch, test_workspace: Path
) -> None:
    settings = _restore_db_test_settings()
    dump_path = (
        test_workspace
        / "data"
        / "restore-db-tests"
        / "1715660000-deadbeef"
        / "vidwiz"
        / "vidwiz-custom-1710000020.sql"
    )
    observed: list[list[str]] = []

    monkeypatch.setattr("scripts.restore_dbs_test.main.wait_ready", lambda *_: None)

    def fake_run(cmd, **kwargs):
        observed.append(cmd)
        return subprocess.CompletedProcess(args=cmd, returncode=0)

    monkeypatch.setattr("scripts.restore_dbs_test.main.subprocess.run", fake_run)

    container = restore_db("vidwiz", dump_path, settings)

    assert container == "restore-test-vidwiz"
    docker_run_cmd = observed[1]
    mount_arg = docker_run_cmd[docker_run_cmd.index("--mount") + 1]

    assert "--mount" in docker_run_cmd
    assert docker_run_cmd[docker_run_cmd.index("--name") + 1] == "restore-test-vidwiz"
    assert mount_arg == f"type=bind,src={dump_path.parent.resolve()},dst=/backups,readonly"


def test_generate_files_uses_home_dir_from_config(test_workspace: Path) -> None:
    config = SchedulerSettings.model_validate(
        {
            "systemd_path": str(test_workspace),
            "uv_bin": "/home/test/.local/bin/uv",
            "working_dir": "/home/test/projects/saarthi",
            "home_dir": "/home/test",
            "scripts": [
                {
                    "name": "saarthi-backup-dbs",
                    "command": "backup-dbs",
                    "time": "04:00",
                    "description": "Backup dbs",
                }
            ],
        }
    )

    timer_names = generate_files(config)

    service_content = (test_workspace / "saarthi-backup-dbs.service").read_text(encoding="utf-8")
    timer_content = (test_workspace / "saarthi-backup-dbs.timer").read_text(encoding="utf-8")

    assert timer_names == ["saarthi-backup-dbs"]
    assert 'Environment="HOME=/home/test"' in service_content
    assert "ExecStart=/home/test/.local/bin/uv run backup-dbs" in service_content
    assert "OnCalendar=*-*-* 04:00:00" in timer_content


def test_setup_logging_defaults_without_validation_error(monkeypatch) -> None:
    observed = {"called": False}

    monkeypatch.setattr("shared.logging.setup.os.makedirs", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "shared.logging.setup.logging.config.dictConfig",
        lambda _cfg: observed.__setitem__("called", True),
    )

    setup_logging()

    assert observed["called"] is True


def test_schedule_scripts_main_bootstrap_is_side_effect_safe(monkeypatch, test_workspace: Path) -> None:
    config = SchedulerSettings.model_validate(
        {
            "systemd_path": str(test_workspace),
            "uv_bin": "/home/test/.local/bin/uv",
            "working_dir": "/home/test/projects/saarthi",
            "home_dir": "/home/test",
            "scripts": [],
        }
    )

    calls = {"generated": 0, "enabled": 0}

    monkeypatch.setattr("shared.logging.setup.os.makedirs", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("shared.logging.setup.logging.config.dictConfig", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("scripts.schedule_scripts.main.load_config", lambda: config)
    monkeypatch.setattr(
        "scripts.schedule_scripts.main.generate_files",
        lambda _config: calls.__setitem__("generated", calls["generated"] + 1) or [],
    )
    monkeypatch.setattr(
        "scripts.schedule_scripts.main.enable_timers",
        lambda _names: calls.__setitem__("enabled", calls["enabled"] + 1),
    )

    exit_code = schedule_main.main()

    assert exit_code == 0
    assert calls["generated"] == 1
    assert calls["enabled"] == 1


def test_schedule_scripts_main_returns_1_on_permission_error(
    monkeypatch,
    test_workspace: Path,
) -> None:
    config = SchedulerSettings.model_validate(
        {
            "systemd_path": str(test_workspace),
            "uv_bin": "/home/test/.local/bin/uv",
            "working_dir": "/home/test/projects/saarthi",
            "home_dir": "/home/test",
            "scripts": [],
        }
    )
    calls = {"enabled": 0}

    monkeypatch.setattr("shared.logging.setup.os.makedirs", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("shared.logging.setup.logging.config.dictConfig", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("scripts.schedule_scripts.main.load_config", lambda: config)
    monkeypatch.setattr(
        "scripts.schedule_scripts.main.generate_files",
        lambda *_: (_ for _ in ()).throw(
            PermissionError(13, "Permission denied", "/etc/systemd/system/demo.service")
        ),
    )
    monkeypatch.setattr(
        "scripts.schedule_scripts.main.enable_timers",
        lambda _names: calls.__setitem__("enabled", calls["enabled"] + 1),
    )

    exit_code = schedule_main.main()

    assert exit_code == 1
    assert calls["enabled"] == 0


def test_dispatch_notifications_respects_channel_toggles(monkeypatch) -> None:
    settings = _backup_db_settings(
        backup_bucket=_BASE_CONFIG["BACKUP_BUCKET"],
        vidwiz_s3_prefix=_BASE_CONFIG["VIDWIZ_S3_PREFIX"],
        trackcrow_s3_prefix=_BASE_CONFIG["TRACKCROW_S3_PREFIX"],
        smashdiary_s3_prefix=_BASE_CONFIG["SMASHDIARY_S3_PREFIX"],
        vidwiz_dump_filename=_BASE_CONFIG["VIDWIZ_DUMP_FILENAME"],
        trackcrow_dump_filename=_BASE_CONFIG["TRACKCROW_DUMP_FILENAME"],
        smashdiary_dump_filename=_BASE_CONFIG["SMASHDIARY_DUMP_FILENAME"],
    )

    calls = {"ntfy": 0, "wa": 0}

    monkeypatch.setattr("scripts.backup_dbs.main.send_ntfy_message", lambda **_: calls.__setitem__("ntfy", calls["ntfy"] + 1))
    monkeypatch.setattr("scripts.backup_dbs.main.send_whatsapp_message", lambda **_: calls.__setitem__("wa", calls["wa"] + 1))

    _dispatch_notifications(
        settings=settings,
        title="DB Backup Success",
        output_lines=["Backup complete for vidwiz"],
        success=True,
    )

    assert calls["ntfy"] == 0
    assert calls["wa"] == 1


def test_restore_dispatch_notifications_respects_channel_toggles(monkeypatch) -> None:
    settings = _restore_db_test_settings()
    calls = {"ntfy": 0, "wa": 0}

    monkeypatch.setattr("scripts.restore_dbs_test.main.send_ntfy_message", lambda **_: calls.__setitem__("ntfy", calls["ntfy"] + 1))
    monkeypatch.setattr("scripts.restore_dbs_test.main.send_whatsapp_message", lambda **_: calls.__setitem__("wa", calls["wa"] + 1))

    dispatch_restore_notifications(
        settings=settings,
        title="DB Restore Verification Success",
        output_lines=["Restore verification passed for vidwiz"],
        success=True,
    )

    assert calls["ntfy"] == 0
    assert calls["wa"] == 1


def test_build_whatsapp_summary_is_concise() -> None:
    output_lines = [
        ">>> rclone copy a b",
        "noise line 1",
        "noise line 2",
        "Backup completed successfully",
    ]

    summary = _build_whatsapp_summary("GDrive Backup Success", output_lines, success=True)

    assert "GDrive Backup Success (SUCCESS)" in summary
    assert len(summary.splitlines()) <= 6


def test_restore_whatsapp_summary_is_concise() -> None:
    output_lines = [
        "noise line 1",
        "Restore verification passed for vidwiz",
        "Restore verification failed for trackcrow: boom",
    ]

    summary = build_restore_whatsapp_summary(
        "DB Restore Verification Failed",
        output_lines,
        success=False,
    )

    assert "DB Restore Verification Failed (FAILED)" in summary
    assert len(summary.splitlines()) <= 4


def test_backup_dbs_main_exit_code_and_notification_title(monkeypatch) -> None:
    settings = _backup_db_settings()
    observed: dict[str, object] = {}

    monkeypatch.setattr("scripts.backup_dbs.main.get_backup_db_settings", lambda: settings)
    monkeypatch.setattr("scripts.backup_dbs.main.setup_logging", lambda *_: None)
    monkeypatch.setattr(
        "scripts.backup_dbs.main.build_db_map",
        lambda *_: {
            "vidwiz": {
                "url": "postgres://vidwiz",
                "filename": "vidwiz-custom",
                "s3_bucket": "my-bucket",
                "s3_prefix": "db/vidwiz",
            }
        },
    )
    monkeypatch.setattr("scripts.backup_dbs.main.run_pg_dump", lambda *_: None)
    monkeypatch.setattr("scripts.backup_dbs.main.sanity_check", lambda *_: None)
    monkeypatch.setattr("scripts.backup_dbs.main.upload_to_s3", lambda **_: None)
    monkeypatch.setattr("scripts.backup_dbs.main.teardown", lambda *_: None)
    monkeypatch.setattr(
        "scripts.backup_dbs.main._dispatch_notifications",
        lambda **kwargs: observed.update(kwargs),
    )

    fail_dump = RuntimeError("boom")
    monkeypatch.setattr(
        "scripts.backup_dbs.main.run_pg_dump",
        lambda *_: (_ for _ in ()).throw(fail_dump),
    )
    exit_code = backup_dbs_main.main()

    assert exit_code == 1
    assert observed["success"] is False
    assert observed["title"] == "DB Backup Failed"

    observed.clear()
    monkeypatch.setattr("scripts.backup_dbs.main.run_pg_dump", lambda *_: None)
    exit_code = backup_dbs_main.main()

    assert exit_code == 0
    assert observed["success"] is True
    assert observed["title"] == "DB Backup Success"


def test_backup_gdrive_main_exit_codes(monkeypatch) -> None:
    settings = _backup_gdrive_settings()
    monkeypatch.setattr("scripts.backup_gdrive.main.get_backup_gdrive_settings", lambda: settings)
    monkeypatch.setattr("scripts.backup_gdrive.main.setup_logging", lambda *_: None)
    monkeypatch.setattr("scripts.backup_gdrive.main.send_whatsapp_message", lambda **_: True)

    monkeypatch.setattr(
        "scripts.backup_gdrive.main.subprocess.run",
        lambda *_, **__: (_ for _ in ()).throw(
            subprocess.CalledProcessError(returncode=1, cmd=["rclone", "copy"])
        ),
    )
    assert backup_gdrive_main.main() == 1

    monkeypatch.setattr(
        "scripts.backup_gdrive.main.subprocess.run",
        lambda *_, **__: subprocess.CompletedProcess(args=["rclone", "copy"], returncode=0),
    )
    exit_code = backup_gdrive_main.main()
    assert exit_code == 0


def test_backup_dbs_main_top_level_failure_dispatches_notification(monkeypatch) -> None:
    settings = _backup_db_settings()
    observed: dict[str, object] = {}

    monkeypatch.setattr("scripts.backup_dbs.main.get_backup_db_settings", lambda: settings)
    monkeypatch.setattr("scripts.backup_dbs.main.setup_logging", lambda *_: None)
    monkeypatch.setattr(
        "scripts.backup_dbs.main.build_db_map",
        lambda *_: (_ for _ in ()).throw(RuntimeError("bootstrap boom")),
    )
    monkeypatch.setattr(
        "scripts.backup_dbs.main._dispatch_notifications",
        lambda **kwargs: observed.update(kwargs),
    )

    exit_code = backup_dbs_main.main()

    assert exit_code == 1
    assert observed["success"] is False
    assert observed["title"] == "DB Backup Failed"


def test_restore_dbs_test_main_exit_code_and_notification_title(monkeypatch) -> None:
    settings = _restore_db_test_settings()
    observed: dict[str, object] = {}
    run_dir = Path(settings.restore_temp_dir) / "1715660000-deadbeef"
    downloads: list[Path] = []

    monkeypatch.setattr("scripts.restore_dbs_test.main.get_restore_db_test_settings", lambda: settings)
    monkeypatch.setattr("scripts.restore_dbs_test.main.setup_logging", lambda *_: None)
    monkeypatch.setattr("scripts.restore_dbs_test.main.create_restore_run_dir", lambda *_: run_dir)
    monkeypatch.setattr(
        "scripts.restore_dbs_test.main.build_restore_db_map",
        lambda *_: {
            "vidwiz": {
                "filename": "vidwiz-custom",
                "s3_bucket": "my-bucket",
                "s3_prefix": "db/vidwiz",
                "test_query": "SELECT 1",
                "expected_output": "1",
            }
        },
    )

    class FakeSession:
        def client(self, name: str):
            assert name == "s3"
            return object()

    monkeypatch.setattr("scripts.restore_dbs_test.main.boto3.Session", lambda **_: FakeSession())
    monkeypatch.setattr("scripts.restore_dbs_test.main.latest_key", lambda *_: "db/vidwiz/vidwiz-custom-1710000020.sql")
    monkeypatch.setattr(
        "scripts.restore_dbs_test.main.download_backup",
        lambda *_args: downloads.append(_args[3]),
    )
    monkeypatch.setattr("scripts.restore_dbs_test.main.teardown", lambda *_: None)
    monkeypatch.setattr(
        "scripts.restore_dbs_test.main._dispatch_notifications",
        lambda **kwargs: observed.update(kwargs),
    )

    fail_restore = RuntimeError("boom")
    monkeypatch.setattr(
        "scripts.restore_dbs_test.main.restore_db",
        lambda *_: (_ for _ in ()).throw(fail_restore),
    )
    monkeypatch.setattr("scripts.restore_dbs_test.main.run_test_query", lambda *_: None)
    exit_code = restore_dbs_test_main.main()

    assert exit_code == 1
    assert observed["success"] is False
    assert observed["title"] == "DB Restore Verification Failed"
    assert downloads == [run_dir / "vidwiz" / "vidwiz-custom-1710000020.sql"]

    observed.clear()
    downloads.clear()
    monkeypatch.setattr("scripts.restore_dbs_test.main.restore_db", lambda *_: "restore-test-vidwiz")
    exit_code = restore_dbs_test_main.main()

    assert exit_code == 0
    assert observed["success"] is True
    assert observed["title"] == "DB Restore Verification Success"
    assert downloads == [run_dir / "vidwiz" / "vidwiz-custom-1710000020.sql"]


def test_restore_dbs_test_main_top_level_failure_dispatches_notification(monkeypatch) -> None:
    settings = _restore_db_test_settings()
    observed: dict[str, object] = {}

    monkeypatch.setattr("scripts.restore_dbs_test.main.get_restore_db_test_settings", lambda: settings)
    monkeypatch.setattr("scripts.restore_dbs_test.main.setup_logging", lambda *_: None)
    monkeypatch.setattr(
        "scripts.restore_dbs_test.main.build_restore_db_map",
        lambda *_: (_ for _ in ()).throw(RuntimeError("bootstrap boom")),
    )
    monkeypatch.setattr(
        "scripts.restore_dbs_test.main._dispatch_notifications",
        lambda **kwargs: observed.update(kwargs),
    )

    exit_code = restore_dbs_test_main.main()

    assert exit_code == 1
    assert observed["success"] is False
    assert observed["title"] == "DB Restore Verification Failed"


def test_restore_dbs_test_main_attempts_teardown_after_failure(monkeypatch) -> None:
    settings = _restore_db_test_settings()
    run_dir = Path(settings.restore_temp_dir) / "1715660000-deadbeef"
    observed = {"called": 0, "temp_dir": None}

    monkeypatch.setattr("scripts.restore_dbs_test.main.get_restore_db_test_settings", lambda: settings)
    monkeypatch.setattr("scripts.restore_dbs_test.main.setup_logging", lambda *_: None)
    monkeypatch.setattr("scripts.restore_dbs_test.main.create_restore_run_dir", lambda *_: run_dir)
    monkeypatch.setattr(
        "scripts.restore_dbs_test.main.build_restore_db_map",
        lambda *_: {
            "vidwiz": {
                "filename": "vidwiz-custom",
                "s3_bucket": "my-bucket",
                "s3_prefix": "db/vidwiz",
                "test_query": "SELECT 1",
                "expected_output": "1",
            }
        },
    )

    class FakeSession:
        def client(self, _name: str):
            return object()

    monkeypatch.setattr("scripts.restore_dbs_test.main.boto3.Session", lambda **_: FakeSession())
    monkeypatch.setattr("scripts.restore_dbs_test.main.latest_key", lambda *_: "db/vidwiz/vidwiz-custom-1710000020.sql")
    monkeypatch.setattr("scripts.restore_dbs_test.main.download_backup", lambda *_: None)
    monkeypatch.setattr(
        "scripts.restore_dbs_test.main.restore_db",
        lambda *_: (_ for _ in ()).throw(RuntimeError("restore failed")),
    )
    monkeypatch.setattr("scripts.restore_dbs_test.main.run_test_query", lambda *_: None)
    monkeypatch.setattr(
        "scripts.restore_dbs_test.main._dispatch_notifications",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "scripts.restore_dbs_test.main.teardown",
        lambda temp_dir, *_: (
            observed.__setitem__("called", observed["called"] + 1),
            observed.__setitem__("temp_dir", temp_dir),
        ),
    )

    exit_code = restore_dbs_test_main.main()

    assert exit_code == 1
    assert observed["called"] == 1
    assert observed["temp_dir"] == run_dir


def test_backup_gdrive_main_top_level_failure_dispatches_notification(monkeypatch) -> None:
    settings = _backup_gdrive_settings()
    observed: dict[str, object] = {}

    monkeypatch.setattr("scripts.backup_gdrive.main.get_backup_gdrive_settings", lambda: settings)
    monkeypatch.setattr("scripts.backup_gdrive.main.setup_logging", lambda *_: None)
    monkeypatch.setattr(
        "scripts.backup_gdrive.main.subprocess.run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("rclone missing")),
    )
    monkeypatch.setattr(
        "scripts.backup_gdrive.main._dispatch_notifications",
        lambda **kwargs: observed.update(kwargs),
    )

    exit_code = backup_gdrive_main.main()

    assert exit_code == 1
    assert observed["success"] is False
    assert observed["title"] == "GDrive Backup Failed"
