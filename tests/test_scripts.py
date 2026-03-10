"""Tests for script configuration behavior."""

import copy
import subprocess
from pathlib import Path
import runpy

from scripts.backup_dbs import main as backup_dbs_main
from scripts.backup_gdrive import main as backup_gdrive_main
from scripts.backup_dbs.main import _dispatch_notifications, build_db_map
from scripts.backup_gdrive.main import _build_whatsapp_summary
from scripts.schedule_scripts.main import generate_files
from shared.settings import BackupDbSettings, BackupGdriveSettings, SchedulerSettings

_EXAMPLE_CONFIG_PATH = Path(__file__).resolve().parents[1] / "app" / "config" / "config.example.py"
_BASE_CONFIG = runpy.run_path(str(_EXAMPLE_CONFIG_PATH))["CONFIG"]


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
        "whatsapp_remote_script_path": "/remote/send.py",
        "whatsapp_target_personal": "1203@s.whatsapp.net",
        "backup_bucket": "my-bucket",
        "vidwiz_s3_prefix": "db/vidwiz",
        "trackcrow_s3_prefix": "db/trackcrow",
        "vidwiz_dump_filename": "vidwiz-custom",
        "trackcrow_dump_filename": "trackcrow-custom",
    }
    defaults.update(overrides)
    return BackupDbSettings(
        **_runtime_kwargs(**defaults),
        aws_access_key="ak",
        aws_secret_access_key="sk",
        vidwiz_db_url="postgres://vidwiz",
        trackcrow_db_url="postgres://trackcrow",
    )


def _backup_gdrive_settings(**overrides) -> BackupGdriveSettings:
    defaults = {
        "ntfy_enabled": False,
        "whatsapp_enabled": True,
        "whatsapp_ssh_host": "pookie",
        "whatsapp_remote_script_path": "/remote/send.py",
        "whatsapp_target_personal": "1203@s.whatsapp.net",
    }
    defaults.update(overrides)
    return BackupGdriveSettings(
        **_runtime_kwargs(**defaults),
        gdrive_source="personal-drive",
        gdrive_destination="dwaar-s3:dwaar/backups/gdrive",
        gdrive_folders=["folder-1"],
    )


def test_build_db_map_uses_settings_values() -> None:
    settings = BackupDbSettings(
        **_runtime_kwargs(),
        aws_access_key="ak",
        aws_secret_access_key="sk",
        vidwiz_db_url="postgres://vidwiz",
        trackcrow_db_url="postgres://trackcrow",
        ntfy_base_url="https://ntfy.example.com",
        ntfy_token="token",
        backup_bucket="my-bucket",
        vidwiz_s3_prefix="db/vidwiz",
        trackcrow_s3_prefix="db/trackcrow",
        vidwiz_dump_filename="vidwiz-custom",
        trackcrow_dump_filename="trackcrow-custom",
    )

    db_map = build_db_map(settings)

    assert db_map["vidwiz"]["s3_bucket"] == "my-bucket"
    assert db_map["vidwiz"]["s3_prefix"] == "db/vidwiz"
    assert db_map["vidwiz"]["filename"] == "vidwiz-custom"
    assert db_map["trackcrow"]["s3_prefix"] == "db/trackcrow"
    assert db_map["trackcrow"]["filename"] == "trackcrow-custom"


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


def test_dispatch_notifications_respects_channel_toggles(monkeypatch) -> None:
    settings = _backup_db_settings(
        backup_bucket=_BASE_CONFIG["BACKUP_BUCKET"],
        vidwiz_s3_prefix=_BASE_CONFIG["VIDWIZ_S3_PREFIX"],
        trackcrow_s3_prefix=_BASE_CONFIG["TRACKCROW_S3_PREFIX"],
        vidwiz_dump_filename=_BASE_CONFIG["VIDWIZ_DUMP_FILENAME"],
        trackcrow_dump_filename=_BASE_CONFIG["TRACKCROW_DUMP_FILENAME"],
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
