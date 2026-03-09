"""Tests for script configuration behavior."""

import subprocess
from pathlib import Path

from scripts.backup_dbs import main as backup_dbs_main
from scripts.backup_gdrive import main as backup_gdrive_main
from scripts.backup_dbs.main import _dispatch_notifications, build_db_map
from scripts.backup_gdrive.main import _build_whatsapp_summary
from scripts.schedule_scripts.main import generate_files
from shared.settings import BackupDbSettings, BackupGdriveSettings, SchedulerSettings


def test_build_db_map_uses_settings_values() -> None:
    settings = BackupDbSettings(
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


def test_generate_files_uses_home_dir_from_config(tmp_path: Path) -> None:
    config = SchedulerSettings.model_validate(
        {
            "systemd_path": str(tmp_path),
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

    service_content = (tmp_path / "saarthi-backup-dbs.service").read_text(encoding="utf-8")
    timer_content = (tmp_path / "saarthi-backup-dbs.timer").read_text(encoding="utf-8")

    assert timer_names == ["saarthi-backup-dbs"]
    assert 'Environment="HOME=/home/test"' in service_content
    assert "ExecStart=/home/test/.local/bin/uv run backup-dbs" in service_content
    assert "OnCalendar=*-*-* 04:00:00" in timer_content


def test_dispatch_notifications_respects_channel_toggles(monkeypatch) -> None:
    settings = BackupDbSettings(
        aws_access_key="ak",
        aws_secret_access_key="sk",
        vidwiz_db_url="postgres://vidwiz",
        trackcrow_db_url="postgres://trackcrow",
        ntfy_enabled=False,
        whatsapp_enabled=True,
        whatsapp_ssh_host="pookie",
        whatsapp_remote_script_path="/remote/send.py",
        whatsapp_target_personal="1203@s.whatsapp.net",
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


def test_backup_dbs_main_returns_non_zero_when_any_db_fails(monkeypatch) -> None:
    settings = BackupDbSettings(
        aws_access_key="ak",
        aws_secret_access_key="sk",
        vidwiz_db_url="postgres://vidwiz",
        trackcrow_db_url="postgres://trackcrow",
        ntfy_enabled=False,
        whatsapp_enabled=True,
        whatsapp_ssh_host="pookie",
        whatsapp_remote_script_path="/remote/send.py",
        whatsapp_target_personal="1203@s.whatsapp.net",
        backup_bucket="my-bucket",
        vidwiz_s3_prefix="db/vidwiz",
        trackcrow_s3_prefix="db/trackcrow",
        vidwiz_dump_filename="vidwiz-custom",
        trackcrow_dump_filename="trackcrow-custom",
    )
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
    monkeypatch.setattr(
        "scripts.backup_dbs.main.run_pg_dump",
        lambda *_: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    monkeypatch.setattr("scripts.backup_dbs.main.teardown", lambda *_: None)
    monkeypatch.setattr(
        "scripts.backup_dbs.main._dispatch_notifications",
        lambda **kwargs: observed.update(kwargs),
    )

    exit_code = backup_dbs_main.main()

    assert exit_code == 1
    assert observed["success"] is False
    assert observed["title"] == "DB Backup Failed"


def test_backup_dbs_main_returns_zero_when_all_dbs_succeed(monkeypatch) -> None:
    settings = BackupDbSettings(
        aws_access_key="ak",
        aws_secret_access_key="sk",
        vidwiz_db_url="postgres://vidwiz",
        trackcrow_db_url="postgres://trackcrow",
        ntfy_enabled=False,
        whatsapp_enabled=True,
        whatsapp_ssh_host="pookie",
        whatsapp_remote_script_path="/remote/send.py",
        whatsapp_target_personal="1203@s.whatsapp.net",
        backup_bucket="my-bucket",
        vidwiz_s3_prefix="db/vidwiz",
        trackcrow_s3_prefix="db/trackcrow",
        vidwiz_dump_filename="vidwiz-custom",
        trackcrow_dump_filename="trackcrow-custom",
    )
    observed: dict[str, object] = {}

    monkeypatch.setattr("scripts.backup_dbs.main.get_backup_db_settings", lambda: settings)
    monkeypatch.setattr("scripts.backup_dbs.main.setup_logging", lambda *_: None)
    monkeypatch.setattr("scripts.backup_dbs.main.run_pg_dump", lambda *_: None)
    monkeypatch.setattr("scripts.backup_dbs.main.sanity_check", lambda *_: None)
    monkeypatch.setattr("scripts.backup_dbs.main.upload_to_s3", lambda **_: None)
    monkeypatch.setattr("scripts.backup_dbs.main.teardown", lambda *_: None)
    monkeypatch.setattr(
        "scripts.backup_dbs.main._dispatch_notifications",
        lambda **kwargs: observed.update(kwargs),
    )

    exit_code = backup_dbs_main.main()

    assert exit_code == 0
    assert observed["success"] is True
    assert observed["title"] == "DB Backup Success"


def test_backup_gdrive_main_returns_non_zero_on_any_folder_failure(monkeypatch) -> None:
    settings = BackupGdriveSettings(
        ntfy_enabled=False,
        whatsapp_enabled=True,
        whatsapp_ssh_host="pookie",
        whatsapp_remote_script_path="/remote/send.py",
        whatsapp_target_personal="1203@s.whatsapp.net",
        gdrive_source="personal-drive",
        gdrive_destination="dwaar-s3:dwaar/backups/gdrive",
        gdrive_folders=["folder-1"],
    )

    monkeypatch.setattr("scripts.backup_gdrive.main.get_backup_gdrive_settings", lambda: settings)
    monkeypatch.setattr("scripts.backup_gdrive.main.setup_logging", lambda *_: None)
    monkeypatch.setattr(
        "scripts.backup_gdrive.main.subprocess.run",
        lambda *_, **__: (_ for _ in ()).throw(
            subprocess.CalledProcessError(returncode=1, cmd=["rclone", "copy"])
        ),
    )
    monkeypatch.setattr("scripts.backup_gdrive.main.send_whatsapp_message", lambda **_: True)

    exit_code = backup_gdrive_main.main()

    assert exit_code == 1


def test_backup_gdrive_main_returns_zero_when_all_folders_succeed(monkeypatch) -> None:
    settings = BackupGdriveSettings(
        ntfy_enabled=False,
        whatsapp_enabled=True,
        whatsapp_ssh_host="pookie",
        whatsapp_remote_script_path="/remote/send.py",
        whatsapp_target_personal="1203@s.whatsapp.net",
        gdrive_source="personal-drive",
        gdrive_destination="dwaar-s3:dwaar/backups/gdrive",
        gdrive_folders=["folder-1"],
    )

    monkeypatch.setattr("scripts.backup_gdrive.main.get_backup_gdrive_settings", lambda: settings)
    monkeypatch.setattr("scripts.backup_gdrive.main.setup_logging", lambda *_: None)
    monkeypatch.setattr(
        "scripts.backup_gdrive.main.subprocess.run",
        lambda *_, **__: subprocess.CompletedProcess(args=["rclone", "copy"], returncode=0),
    )
    monkeypatch.setattr("scripts.backup_gdrive.main.send_whatsapp_message", lambda **_: True)

    exit_code = backup_gdrive_main.main()

    assert exit_code == 0
