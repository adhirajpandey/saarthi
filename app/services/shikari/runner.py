"""Orchestration helpers for Shikari session visualization."""

from dataclasses import dataclass
import html
from pathlib import Path
from typing import Any

from app.services.shikari.loader import list_sessions, load_meta, load_session
from app.services.shikari.plots import plot_session_dashboard
from shared.settings import ShikariSettings

REQUIRED_SESSION_FILES = ("meta/device.csv",)
PLOTLY_HTML_INCLUDE_JS = "cdn"
PLOTLY_HTML_FULL = True
PLOTLY_HTML_CONFIG = {"scrollZoom": True}


@dataclass(slots=True)
class VisualizationResult:
    session_name: str
    device: str
    duration_s: float
    sensor_names: list[str]
    output_paths: list[Path]


def looks_like_session_dir(session_dir: Path) -> bool:
    """Cheap structural validation for a session directory."""
    if not session_dir.is_dir():
        return False

    if not all((session_dir / rel).is_file() for rel in REQUIRED_SESSION_FILES):
        return False

    return any(session_dir.glob("*.csv"))


def list_candidate_sessions(data_dir: Path) -> list[Path]:
    """Return valid session directories sorted by name."""
    candidates = list_sessions(data_dir)
    return [session_dir for session_dir in candidates if looks_like_session_dir(session_dir)]


def resolve_session_dir(data_dir: Path, session_name: str | None) -> Path:
    """Return selected session directory or raise ValueError."""
    sessions = list_candidate_sessions(data_dir)
    if not sessions:
        raise ValueError(f"No session directories found in {data_dir}")

    if session_name:
        session_dir = data_dir / session_name
        if not session_dir.is_dir():
            raise ValueError(f"Session directory not found: {session_dir}")
        return session_dir

    return sessions[-1]


def resolve_data_dir(settings: ShikariSettings, data_dir_override: Path | None) -> Path:
    """Resolve session data path from CLI override or settings."""
    return data_dir_override if data_dir_override is not None else Path(settings.shikari_sessions_path)


def resolve_output_dir(settings: ShikariSettings) -> Path:
    """Resolve output directory from settings."""
    return Path(settings.shikari_outputs_path)


def _write_html(fig: Any, path: Path, tab_title: str) -> None:
    body = fig.to_html(
        include_plotlyjs=PLOTLY_HTML_INCLUDE_JS,
        full_html=False,
        config=PLOTLY_HTML_CONFIG,
    )
    if PLOTLY_HTML_FULL:
        safe_title = html.escape(tab_title)
        content = (
            "<!DOCTYPE html>"
            "<html>"
            "<head>"
            '<meta charset="utf-8" />'
            f"<title>{safe_title}</title>"
            "</head>"
            "<body>"
            f"{body}"
            "</body>"
            "</html>"
        )
    else:
        content = body
    path.write_text(content, encoding="utf-8")


def _write_static_image(fig: Any, path: Path) -> None:
    fig.write_image(str(path))


def render_session_outputs(
    *,
    session_dir: Path,
    output_dir: Path,
    output_formats: list[str],
    theme: str,
) -> VisualizationResult:
    """Load a session and generate all requested dashboard outputs."""
    session_data = load_session(session_dir)
    meta = load_meta(session_dir, session_data=session_data)
    fig = plot_session_dashboard(session_data, meta, theme=theme)

    tab_title = session_dir.name
    output_stem = f"trip_{tab_title}_sensors"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_paths: list[Path] = []
    for fmt in output_formats:
        out_path = output_dir / f"{output_stem}.{fmt}"
        if fmt == "html":
            _write_html(fig, out_path, tab_title)
        else:
            _write_static_image(fig, out_path)
        output_paths.append(out_path.resolve())

    return VisualizationResult(
        session_name=session_dir.name,
        device=meta.get("device", {}).get("deviceModel", "?"),
        duration_s=float(meta.get("duration_s", 0)),
        sensor_names=[key for key in session_data if not key.startswith("meta/")],
        output_paths=output_paths,
    )
