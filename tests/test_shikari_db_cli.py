"""Tests for the Shikari database management CLI."""

from pathlib import Path
from types import SimpleNamespace

from app.services.shikari.storage import verify_database
from scripts.shikari_db import main as shikari_db_main


def _write_session(base_dir: Path, name: str) -> Path:
    session_dir = base_dir / name
    session_dir.mkdir(parents=True)
    (session_dir / "Location.csv").write_text(
        '"Time (s)","Latitude (°)","Longitude (°)","Height (m)","Velocity (m/s)","Direction (°)","Horizontal Accuracy (m)","Vertical Accuracy (m)"\n'
        "0,28.4,77.0,250,0,0,4,6\n",
        encoding="utf-8",
    )
    meta_dir = session_dir / "meta"
    meta_dir.mkdir()
    (meta_dir / "device.csv").write_text(
        '"property","value"\n"deviceModel","Pixel 6a"\n',
        encoding="utf-8",
    )
    (meta_dir / "time.csv").write_text(
        '"event","experiment time","system time","system time text"\n'
        '"START",0,1770000000,"2026-02-02 20:10:00.000 UTC+05:30"\n'
        '"PAUSE",0,1770000000,"2026-02-02 20:10:00.000 UTC+05:30"\n',
        encoding="utf-8",
    )
    return session_dir


def _settings(test_workspace: Path, sessions_dir: Path, db_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        shikari_sessions_path=str(sessions_dir),
        shikari_db_path=str(db_path),
        logging_settings=lambda: None,
    )


def test_cli_import_all_and_verify(monkeypatch, capsys, test_workspace: Path) -> None:
    sessions_dir = test_workspace / "sessions"
    _write_session(sessions_dir, "2026-02-02-20:10:00")
    db_path = test_workspace / "rides.sqlite3"
    monkeypatch.setattr(
        shikari_db_main,
        "get_shikari_settings",
        lambda: _settings(test_workspace, sessions_dir, db_path),
    )
    monkeypatch.setattr(shikari_db_main, "setup_logging", lambda *_: None)
    monkeypatch.setattr("sys.argv", ["shikari-db", "import", "--all"])

    assert shikari_db_main.main() == 0
    assert "Imported 1 source session(s)" in capsys.readouterr().out
    assert verify_database(db_path).sample_count == 1

    monkeypatch.setattr("sys.argv", ["shikari-db", "verify"])
    assert shikari_db_main.main() == 0
    assert "Integrity: ok" in capsys.readouterr().out


def test_cli_backup_creates_verified_snapshot(monkeypatch, capsys, test_workspace: Path) -> None:
    sessions_dir = test_workspace / "sessions"
    source_dir = _write_session(sessions_dir, "2026-02-02-20:10:00")
    db_path = test_workspace / "rides.sqlite3"
    backup_path = test_workspace / "backup" / "rides.sqlite3"
    from app.services.shikari.importer import import_session

    import_session(db_path, source_dir)
    monkeypatch.setattr(
        shikari_db_main,
        "get_shikari_settings",
        lambda: _settings(test_workspace, sessions_dir, db_path),
    )
    monkeypatch.setattr(shikari_db_main, "setup_logging", lambda *_: None)
    monkeypatch.setattr(
        "sys.argv",
        ["shikari-db", "backup", str(backup_path)],
    )

    assert shikari_db_main.main() == 0
    assert backup_path.is_file()
    assert "Backup verified" in capsys.readouterr().out
