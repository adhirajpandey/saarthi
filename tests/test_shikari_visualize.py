"""Tests for Shikari visualization services and CLI."""

from pathlib import Path
from types import SimpleNamespace

from app.services.shikari.runner import (
    VisualizationResult,
    list_candidate_sessions,
    resolve_data_dir,
    resolve_session_dir,
)
from scripts.shikari_visualize import main as shikari_main


def _make_session(base_dir: Path, name: str, *, with_device: bool = True) -> Path:
    session_dir = base_dir / name
    session_dir.mkdir(parents=True)
    (session_dir / "Location.csv").write_text(
        '"Time (s)","Latitude (°)","Longitude (°)","Height (m)","Velocity (m/s)","Direction (°)","Horizontal Accuracy (m)","Vertical Accuracy (m)"\n'
        "0,12.1,77.1,900,0,0,1,1\n",
        encoding="utf-8",
    )
    meta_dir = session_dir / "meta"
    meta_dir.mkdir()
    if with_device:
        (meta_dir / "device.csv").write_text('"property","value"\n"deviceModel","Pixel"\n', encoding="utf-8")
    return session_dir


def test_list_candidate_sessions_filters_invalid_dirs(test_workspace: Path) -> None:
    data_dir = test_workspace / "sessions"
    data_dir.mkdir()
    _make_session(data_dir, "2026-02-24-11:12:51", with_device=True)
    _make_session(data_dir, "2026-02-25-11:12:51", with_device=False)

    sessions = list_candidate_sessions(data_dir)

    assert [session.name for session in sessions] == ["2026-02-24-11:12:51"]


def test_resolve_session_dir_defaults_to_latest(test_workspace: Path) -> None:
    data_dir = test_workspace / "sessions"
    data_dir.mkdir()
    _make_session(data_dir, "2026-02-24-11:12:51")
    _make_session(data_dir, "2026-02-25-11:12:51")

    resolved = resolve_session_dir(data_dir, session_name=None)

    assert resolved.name == "2026-02-25-11:12:51"


def test_resolve_data_dir_uses_override(test_workspace: Path) -> None:
    default_data = test_workspace / "default-sessions"
    override_data = test_workspace / "override-sessions"
    settings = SimpleNamespace(shikari_sessions_path=str(default_data))

    assert resolve_data_dir(settings, override_data) == override_data


def test_shikari_cli_list_sessions(monkeypatch, capsys, test_workspace: Path) -> None:
    data_dir = test_workspace / "sessions"
    data_dir.mkdir()
    _make_session(data_dir, "2026-02-24-11:12:51")
    settings = SimpleNamespace(
        shikari_default_output_format="png",
        shikari_default_theme="dark",
        shikari_sessions_path=str(data_dir),
        shikari_outputs_path=str(test_workspace / "outputs"),
        logging_settings=lambda: None,
    )

    monkeypatch.setattr(shikari_main, "get_shikari_settings", lambda: settings)
    monkeypatch.setattr(shikari_main, "setup_logging", lambda *_: None)
    monkeypatch.setattr(
        "sys.argv",
        ["shikari-visualize", "--list"],
    )

    exit_code = shikari_main.main()
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "Found 1 session(s)" in out
    assert "2026-02-24-11:12:51" in out


def test_shikari_cli_invokes_renderer(monkeypatch, capsys, test_workspace: Path) -> None:
    data_dir = test_workspace / "sessions"
    data_dir.mkdir()
    _make_session(data_dir, "2026-02-24-11:12:51")
    output_dir = test_workspace / "outputs"
    settings = SimpleNamespace(
        shikari_default_output_format="png",
        shikari_default_theme="dark",
        shikari_sessions_path=str(data_dir),
        shikari_outputs_path=str(output_dir),
        logging_settings=lambda: None,
    )
    observed: dict[str, object] = {}

    def _fake_render_session_outputs(**kwargs):
        observed.update(kwargs)
        return VisualizationResult(
            session_name="2026-02-24-11:12:51",
            device="Pixel 6a",
            duration_s=12.3,
            sensor_names=["Location", "Accelerometer"],
            output_paths=[output_dir / "trip_2026-02-24-11:12:51_sensors.png"],
        )

    monkeypatch.setattr(shikari_main, "get_shikari_settings", lambda: settings)
    monkeypatch.setattr(shikari_main, "setup_logging", lambda *_: None)
    monkeypatch.setattr(shikari_main, "render_session_outputs", _fake_render_session_outputs)
    monkeypatch.setattr(
        "sys.argv",
        ["shikari-visualize", "2026-02-24-11:12:51", "--output", "png", "html"],
    )

    exit_code = shikari_main.main()
    out = capsys.readouterr().out

    assert exit_code == 0
    assert observed["theme"] == "dark"
    assert observed["output_formats"] == ["png", "html"]
    assert "Device : Pixel 6a" in out
    assert "Generating output(s): png, html" in out


def test_shikari_cli_fails_when_data_dir_missing(monkeypatch, capsys, test_workspace: Path) -> None:
    settings = SimpleNamespace(
        shikari_default_output_format="png",
        shikari_default_theme="dark",
        shikari_sessions_path=str(test_workspace / "missing"),
        shikari_outputs_path=str(test_workspace / "outputs"),
        logging_settings=lambda: None,
    )

    monkeypatch.setattr(shikari_main, "get_shikari_settings", lambda: settings)
    monkeypatch.setattr(shikari_main, "setup_logging", lambda *_: None)
    monkeypatch.setattr("sys.argv", ["shikari-visualize"])

    exit_code = shikari_main.main()
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "Data directory not found" in out
