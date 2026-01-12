#!/usr/bin/env python3
"""
Generate systemd service and timer files from config.

Usage:
    sudo python3 main.py

Useful Commands:
    # List all timers
    systemctl list-timers --all | grep saarthi

    # Check service status
    systemctl status saarthi-backup-dbs.service

    # Manually trigger a service
    sudo systemctl start saarthi-backup-dbs.service

    # View logs
    journalctl -u saarthi-backup-dbs.service -n 50

    # Follow logs in real-time
    journalctl -u saarthi-backup-dbs.service -f

    # Disable a timer
    sudo systemctl disable --now saarthi-backup-dbs.timer
"""

import json
import subprocess
from pathlib import Path

SERVICE_TEMPLATE = """[Unit]
Description={description}

[Service]
Type=oneshot
ExecStart={python_venv} {script_path}
WorkingDirectory={working_dir}
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
Environment="HOME=/home/adhiraj"
"""

TIMER_TEMPLATE = """[Unit]
Description=Timer for {name}

[Timer]
OnCalendar=*-*-* {time}:00
Persistent=true

[Install]
WantedBy=timers.target
"""


def load_config():
    config_path = Path(__file__).parent / "config.json"
    with open(config_path) as f:
        return json.load(f)


def generate_files(config):
    systemd_path = Path(config["systemd_path"])
    python_venv = config["python_venv"]
    timer_names = []

    for script in config["scripts"]:
        name = script["name"]
        script_path = script["path"]
        working_dir = str(Path(script_path).parent)
        timer_names.append(name)

        service_content = SERVICE_TEMPLATE.format(
            description=script.get("description", name),
            python_venv=python_venv,
            script_path=script_path,
            working_dir=working_dir,
        )

        timer_content = TIMER_TEMPLATE.format(
            name=name,
            time=script["time"],
        )

        service_file = systemd_path / f"{name}.service"
        timer_file = systemd_path / f"{name}.timer"

        print(f"Writing {service_file}")
        with open(service_file, "w") as f:
            f.write(service_content)

        print(f"Writing {timer_file}")
        with open(timer_file, "w") as f:
            f.write(timer_content)

    return timer_names


def enable_timers(timer_names):
    print("\nReloading systemd daemon...")
    subprocess.run(["systemctl", "daemon-reload"], check=True)

    for name in timer_names:
        print(f"Enabling {name}.timer...")
        subprocess.run(["systemctl", "enable", "--now", f"{name}.timer"], check=True)

    print("\nAll timers enabled.")


if __name__ == "__main__":
    config = load_config()
    timer_names = generate_files(config)
    enable_timers(timer_names)
