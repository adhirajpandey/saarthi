"""Generate and enable systemd service/timer files from config."""

import json
import subprocess
from pathlib import Path

SERVICE_TEMPLATE = """[Unit]
Description={description}

[Service]
Type=oneshot
ExecStart={exec_start}
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


def load_config() -> dict:
    repo_root = Path(__file__).resolve().parents[2]
    config_path = repo_root / "scripts" / "schedule-scripts" / "config.json"
    with open(config_path, encoding="utf-8") as file:
        return json.load(file)


def generate_files(config: dict) -> list[str]:
    systemd_path = Path(config["systemd_path"])
    uv_bin = config["uv_bin"]
    working_dir = config["working_dir"]
    timer_names: list[str] = []

    for script in config["scripts"]:
        name = script["name"]
        command = script["command"]
        exec_start = f"{uv_bin} run {command}"
        timer_names.append(name)

        service_content = SERVICE_TEMPLATE.format(
            description=script.get("description", name),
            exec_start=exec_start,
            working_dir=working_dir,
        )
        timer_content = TIMER_TEMPLATE.format(name=name, time=script["time"])

        service_file = systemd_path / f"{name}.service"
        timer_file = systemd_path / f"{name}.timer"

        print(f"Writing {service_file}")
        with open(service_file, "w", encoding="utf-8") as file:
            file.write(service_content)

        print(f"Writing {timer_file}")
        with open(timer_file, "w", encoding="utf-8") as file:
            file.write(timer_content)

    return timer_names


def enable_timers(timer_names: list[str]) -> None:
    print("\nReloading systemd daemon...")
    subprocess.run(["systemctl", "daemon-reload"], check=True)

    for name in timer_names:
        print(f"Enabling {name}.timer...")
        subprocess.run(["systemctl", "enable", "--now", f"{name}.timer"], check=True)

    print("\nAll timers enabled.")


def main() -> None:
    config = load_config()
    timer_names = generate_files(config)
    enable_timers(timer_names)


if __name__ == "__main__":
    main()

