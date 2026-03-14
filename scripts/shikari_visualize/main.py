"""Shikari visualization CLI."""

import argparse
import logging
import sys
from pathlib import Path

from app.services.shikari.constants import OUTPUT_FORMATS, THEMES
from app.services.shikari.runner import (
    list_candidate_sessions,
    render_session_outputs,
    resolve_data_dir,
    resolve_output_dir,
    resolve_session_dir,
)
from shared.logging import setup_logging
from shared.settings import get_shikari_settings

logger = logging.getLogger(__name__)


def _parse_args(default_format: str, default_theme: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Visualize bike ride sensor sessions with interactive Plotly dashboards.",
        epilog=(
            "Examples:\n"
            "  uv run shikari-visualize --list\n"
            "\n"
            "  uv run shikari-visualize 2026-02-24-11:12:51 "
            "--data-dir ./data/shikari/sessions --output png html --theme dark"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "session",
        nargs="?",
        default=None,
        help="Ride session directory name (e.g. '2026-02-24-11:12:51'). Defaults to latest.",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        dest="list_sessions",
        help="List available ride sessions and exit.",
    )
    parser.add_argument(
        "--data-dir",
        "-d",
        type=Path,
        default=None,
        help="Path containing ride session directories.",
    )
    parser.add_argument(
        "--output",
        nargs="+",
        choices=OUTPUT_FORMATS,
        metavar="FORMAT",
        default=[default_format],
        help=f"Output format(s) to generate (default: {default_format}).",
    )
    parser.add_argument(
        "--output-format",
        nargs="+",
        choices=OUTPUT_FORMATS,
        metavar="FORMAT",
        dest="output",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--theme",
        choices=THEMES,
        metavar="THEME",
        default=default_theme,
        help=f"Theme for generated dashboards (default: {default_theme}).",
    )
    return parser.parse_args()


def main() -> int:
    try:
        settings = get_shikari_settings()
        setup_logging(settings.logging_settings())
        args = _parse_args(
            default_format=settings.shikari_default_output_format,
            default_theme=settings.shikari_default_theme,
        )
        data_dir = resolve_data_dir(settings, args.data_dir)
        if not data_dir.is_dir():
            print(f"Data directory not found: {data_dir}")
            return 1

        sessions = list_candidate_sessions(data_dir)
        if not sessions:
            print(f"No session directories found in {data_dir}")
            return 1

        if args.list_sessions:
            print(f"Found {len(sessions)} session(s) in {data_dir}:\n")
            for session in sessions:
                print(f"  {session.name}")
            return 0

        session_dir = resolve_session_dir(data_dir, args.session)
        output_dir = resolve_output_dir(settings)
        requested_formats = list(dict.fromkeys(args.output))

        print(f"Loading session: {session_dir.name}")
        result = render_session_outputs(
            session_dir=session_dir,
            output_dir=output_dir,
            output_formats=requested_formats,
            theme=args.theme,
        )
        print(f"  Device : {result.device}")
        print(f"  Duration: {result.duration_s:.1f} s")
        print(f"  Sensors : {', '.join(result.sensor_names)}")
        print(f"\nGenerating output(s): {', '.join(requested_formats)}")
        print(f"Theme: {args.theme}")
        for path in result.output_paths:
            print(f"{path.suffix[1:].upper()} saved to: {path}")

        return 0
    except Exception as exc:
        logger.exception("Failed to run shikari visualization")
        print(f"Failed to run shikari visualization: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
