"""Generate and enable systemd service/timer files from config."""

import json
import logging
import subprocess
import sys
from pathlib import Path

from shared.logging import setup_logging
from shared.settings import SchedulerSettings

logger = logging.getLogger(__name__)

SERVICE_TEMPLATE = """[Unit]
Description={description}

[Service]
Type=oneshot
User={run_user}
Group={run_group}
ExecStart={exec_start}
WorkingDirectory={working_dir}
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
Environment="HOME={home_dir}"
"""

TIMER_TEMPLATE = """[Unit]
Description=Timer for {name}

[Timer]
OnCalendar=*-*-* {time}:00
Persistent=true

[Install]
WantedBy=timers.target
"""


def load_config() -> SchedulerSettings:
    repo_root = Path(__file__).resolve().parents[2]
    config_path = repo_root / "scripts" / "schedule_scripts" / "config.json"
    with open(config_path, encoding="utf-8") as file:
        payload = json.load(file)
    return SchedulerSettings.model_validate(payload)


def generate_files(config: SchedulerSettings) -> list[str]:
    systemd_path = Path(config.systemd_path)
    uv_bin = config.uv_bin
    working_dir = config.working_dir
    timer_names: list[str] = []
    run_user = Path(config.home_dir).name
    run_group = run_user

    for script in config.scripts:
        name = script.name
        command = script.command
        exec_start = f"{uv_bin} run {command}"
        timer_names.append(name)

        service_content = SERVICE_TEMPLATE.format(
            description=script.description,
            run_user=run_user,
            run_group=run_group,
            exec_start=exec_start,
            working_dir=working_dir,
            home_dir=config.home_dir,
        )
        timer_content = TIMER_TEMPLATE.format(name=name, time=script.time)

        service_file = systemd_path / f"{name}.service"
        timer_file = systemd_path / f"{name}.timer"

        logger.info("Writing %s", service_file)
        with open(service_file, "w", encoding="utf-8") as file:
            file.write(service_content)

        logger.info("Writing %s", timer_file)
        with open(timer_file, "w", encoding="utf-8") as file:
            file.write(timer_content)

    return timer_names


def enable_timers(timer_names: list[str]) -> None:
    logger.info("Reloading systemd daemon")
    subprocess.run(["systemctl", "daemon-reload"], check=True)

    for name in timer_names:
        logger.info("Enabling %s.timer", name)
        subprocess.run(["systemctl", "enable", "--now", f"{name}.timer"], check=True)

    logger.info("All timers enabled")


def main() -> int:
    setup_logging()
    try:
        config = load_config()
        timer_names = generate_files(config)
        enable_timers(timer_names)
        return 0
    except PermissionError as exc:
        target = exc.filename or "configured systemd path"
        logger.error(
            "Permission denied while writing systemd units (%s). "
            "Run with elevated privileges or change systemd_path.",
            target,
        )
        return 1
    except subprocess.CalledProcessError as exc:
        logger.error("systemctl command failed: %s", exc)
        return 1
    except Exception:
        logger.exception("Failed to configure scheduler scripts")
        return 1


if __name__ == "__main__":
    sys.exit(main())
