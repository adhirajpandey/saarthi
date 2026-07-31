"""Manage the canonical Shikari SQLite ride archive."""

import argparse
from collections import Counter
import logging
from pathlib import Path
import sys

from app.services.shikari.importer import import_session
from app.services.shikari.runner import list_candidate_sessions
from app.services.shikari.storage import backup_database, verify_database
from shared.logging import setup_logging
from shared.settings import get_shikari_settings


logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manage the Shikari SQLite ride archive.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    import_parser = subparsers.add_parser("import", help="Import Shikari session folders.")
    import_parser.add_argument("sessions", nargs="*", help="Session directory names to import.")
    import_parser.add_argument(
        "--all",
        action="store_true",
        dest="all_sessions",
        help="Import every valid session in the source directory.",
    )
    import_parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Override the configured source session directory.",
    )
    import_parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Override the configured ride database path.",
    )

    verify_parser = subparsers.add_parser("verify", help="Verify database integrity and counts.")
    verify_parser.add_argument("--db", type=Path, default=None)

    backup_parser = subparsers.add_parser("backup", help="Create and verify an online backup.")
    backup_parser.add_argument("destination", type=Path)
    backup_parser.add_argument("--db", type=Path, default=None)
    return parser.parse_args()


def _print_verification(report) -> None:
    print(f"Integrity: {report.integrity_result}")
    print(f"Foreign keys: {'ok' if not report.foreign_key_errors else 'failed'}")
    print(f"Rides: {report.ride_count}")
    print(f"Imports: {report.import_count}")
    print(f"Samples: {report.sample_count}")


def _run_import(args: argparse.Namespace, settings) -> int:
    data_dir = args.data_dir or Path(settings.shikari_sessions_path)
    db_path = args.db or Path(settings.shikari_db_path)
    if not data_dir.is_dir():
        raise ValueError(f"Data directory not found: {data_dir}")
    if args.all_sessions and args.sessions:
        raise ValueError("Pass session names or --all, not both")
    if args.all_sessions:
        session_dirs = list_candidate_sessions(data_dir)
    elif args.sessions:
        session_dirs = [data_dir / name for name in args.sessions]
    else:
        raise ValueError("Pass at least one session name or --all")
    if not session_dirs:
        raise ValueError(f"No valid session directories found in {data_dir}")

    statuses: Counter[str] = Counter()
    failures: list[tuple[Path, Exception]] = []
    for session_dir in session_dirs:
        try:
            result = import_session(db_path, session_dir)
            statuses[result.status] += 1
            print(
                f"{session_dir.name}: {result.status} "
                f"(ride={result.ride_id}, samples={result.sample_count})"
            )
        except Exception as exc:
            logger.exception("Failed to import Shikari session %s", session_dir)
            failures.append((session_dir, exc))
            print(f"{session_dir.name}: failed: {exc}", file=sys.stderr)

    print(f"Imported {len(session_dirs) - len(failures)} source session(s) into {db_path}")
    if statuses:
        print("Statuses: " + ", ".join(f"{key}={value}" for key, value in sorted(statuses.items())))
    if failures:
        print(f"Failed sessions: {len(failures)}", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    try:
        settings = get_shikari_settings()
        setup_logging(settings.logging_settings())
        args = _parse_args()
        db_path = args.db or Path(settings.shikari_db_path)
        if args.command == "import":
            return _run_import(args, settings)
        if args.command == "verify":
            report = verify_database(db_path)
            _print_verification(report)
            return 0 if report.ok else 1
        if args.command == "backup":
            report = backup_database(db_path, args.destination)
            _print_verification(report)
            print(f"Backup verified: {args.destination}")
            return 0 if report.ok else 1
        raise ValueError(f"Unknown command: {args.command}")
    except Exception as exc:
        logger.exception("Shikari database command failed")
        print(f"Shikari database command failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
