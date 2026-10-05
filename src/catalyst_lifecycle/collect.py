"""Save show output from IOS-XE devices over SSH, for the parser and the backups to read later.

Read-only: every command goes through _show(), which refuses anything that isn't on the
allowlist, and nothing here enters configuration mode.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from netmiko import ConnectHandler

from catalyst_lifecycle.parse import command_file

READ_ONLY_COMMANDS = ("show version", "show inventory", "show running-config")


@dataclass
class Target:
    name: str
    host: str
    port: int = 22
    device_type: str = "cisco_xe"
    username_env: str = "SANDBOX_USERNAME"
    password_env: str = "SANDBOX_PASSWORD"  # noqa: S105 (the name of an env var, not a password)


def load_targets(path: Path) -> list[Target]:
    return [Target(**item) for item in yaml.safe_load(path.read_text())["devices"]]


def _show(conn, command: str) -> str:
    if command not in READ_ONLY_COMMANDS:
        raise ValueError(f"{command!r} is not on the read-only allowlist")
    return conn.send_command(command, read_timeout=90)


def collect(target: Target, out_dir: Path) -> Path:
    """Run the allowlisted commands on one device and save each output as a text file."""
    username, password = os.environ.get(target.username_env), os.environ.get(target.password_env)
    if not username or not password:
        raise RuntimeError(f"{target.name}: set {target.username_env} and {target.password_env} in .env")
    params = {
        "device_type": target.device_type,
        "host": target.host,
        "port": target.port,
        "username": username,
        "password": password,
        "conn_timeout": 20,
    }
    with ConnectHandler(**params) as conn:
        outputs = {command: _show(conn, command) for command in READ_ONLY_COMMANDS}
    folder = out_dir / target.name
    folder.mkdir(parents=True, exist_ok=True)
    for command, text in outputs.items():
        (folder / command_file(command)).write_text(text.rstrip("\n") + "\n")
    return folder
