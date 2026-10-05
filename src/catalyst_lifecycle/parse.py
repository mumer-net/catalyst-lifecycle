"""Turn saved show output into a list of parts, with ntc-templates doing the parsing.

A device is a folder of text files named after their commands: show_version.txt,
show_inventory.txt, show_running-config.txt, and, for some of the public 4500 samples,
show_module.txt.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from ntc_templates.parse import parse_output

# The public samples of older 4500 supervisors are show module captures, so that file is read
# too, though collect.py never runs the command.
COMMANDS = ("show version", "show inventory", "show module", "show running-config")
CHASSIS_TYPE = re.compile(r"^Chassis Type\s*:\s*(\S+)", re.MULTILINE)


@dataclass(frozen=True)
class Part:
    device: str
    name: str
    pid: str
    serial: str
    description: str
    source: str


@dataclass
class Device:
    name: str
    hostname: str = ""
    version: str = ""
    parts: list[Part] = field(default_factory=list)


def command_file(command: str) -> str:
    return command.replace(" ", "_") + ".txt"


def _parse(command: str, text: str) -> list[dict]:
    # ntc-templates has no cisco_xe templates; IOS XE output parses with the cisco_ios ones.
    return parse_output(platform="cisco_ios", command=command, data=text)


def parts_from_inventory(device: str, text: str) -> list[Part]:
    # ntc-templates keeps the padding after VID (for example "V09  "), and NAME and DESCR can
    # end in a space inside their quotes, so every field is stripped.
    return [
        Part(device, r["name"].strip(), r["pid"].strip(), r["sn"].strip(), r["descr"].strip(), "show inventory")
        for r in _parse("show inventory", text)
    ]


def parts_from_module(device: str, text: str) -> list[Part]:
    parts = []
    chassis = CHASSIS_TYPE.search(text)  # ntc-templates skips this line
    if chassis:
        parts.append(Part(device, "Chassis", chassis.group(1), "", "", "show module"))
    for r in _parse("show module", text):
        if not r["model"]:  # an empty supervisor slot
            continue
        name = f"Module {r['module']}"
        if r.get("switch_number"):
            name = f"Switch {r['switch_number']} {name.lower()}"
        parts.append(Part(device, name, r["model"], r["serial"], r["cardtype"], "show module"))
    return parts


def parts_from_version(device: str, version: dict) -> list[Part]:
    models, serials = version.get("hardware") or [], version.get("serial") or []
    parts = []
    for i, pid in enumerate(models):
        name = "Chassis" if len(models) == 1 else f"Chassis {i + 1}"
        serial = serials[i] if i < len(serials) else ""
        parts.append(Part(device, name, pid, serial, "", "show version"))
    return parts


def load_device(folder: Path) -> Device:
    device = Device(folder.name)
    files = {command: folder / command_file(command) for command in COMMANDS}
    version: dict = {}
    if files["show version"].exists():
        rows = _parse("show version", files["show version"].read_text())
        version = rows[0] if rows else {}
        device.hostname, device.version = version.get("hostname", ""), version.get("version", "")
    # show inventory lists everything, chassis included, so the other sources are fallbacks.
    if files["show inventory"].exists():
        device.parts = parts_from_inventory(device.name, files["show inventory"].read_text())
    elif files["show module"].exists():
        device.parts = parts_from_module(device.name, files["show module"].read_text())
    else:
        device.parts = parts_from_version(device.name, version)
    return device


def load_devices(path: Path) -> list[Device]:
    """Load one device folder, or every device folder inside path."""
    if any(path.glob("show_*.txt")):
        return [load_device(path)]
    return [load_device(folder) for folder in sorted(path.iterdir()) if any(folder.glob("show_*.txt"))]
