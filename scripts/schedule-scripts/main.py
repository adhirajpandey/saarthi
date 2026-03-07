"""Backward-compatible wrapper for schedule generation."""

import subprocess


if __name__ == "__main__":
    raise SystemExit(subprocess.call(["uv", "run", "schedule-scripts"]))
