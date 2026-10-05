"""Back up running configs to a local Git repo: one file per device, one commit per change.

Before a config is written, lines that change on every read (byte counts, timestamps) are
dropped and secrets are masked, so a commit means the config really changed and nothing
secret lands in Git. The repo is meant to stay on the machine that runs the backups.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

VOLATILE = re.compile(
    r"^(Building configuration|Current configuration :|! Last configuration change|"
    r"! NVRAM config last updated|! No configuration change since last restart|ntp clock-period)"
)
SECRETS = [
    # enable secret 9 ..., username x secret 9 ..., line "password 7 ...", "password cisco"
    re.compile(r"(?P<head>\b(?:secret|password)\s+(?!encryption\b)(?:[0-9]\s+)?)(?P<value>\S+)"),
    # key chains, and RADIUS/TACACS server blocks: " key-string 7 ...", " key 7 ..."
    re.compile(r"(?P<head>^\s*key-string\s+(?:[0-9]\s+)?)(?P<value>\S+)"),
    re.compile(r"(?P<head>^\s*key\s+(?!chain\b|config-key\b|\d+\s*$)(?:[0-9]\s+)?)(?P<value>\S+)"),
    re.compile(r"(?P<head>^(?:tacacs|radius)-server\b.*?\bkey\s+(?:[0-9]\s+)?)(?P<value>\S+)"),
    # OSPF, NTP, and IKE keys, and SNMP communities, which are passwords too
    re.compile(r"(?P<head>\bip ospf authentication-key\s+(?:[07]\s+)?)(?P<value>\S+)"),
    re.compile(r"(?P<head>\bmessage-digest-key\s+\d+\s+md5\s+(?:[07]\s+)?)(?P<value>\S+)"),
    re.compile(r"(?P<head>\bntp authentication-key\s+\d+\s+\S+\s+)(?P<value>\S+)"),
    re.compile(r"(?P<head>\bcrypto isakmp key\s+(?:[06]\s+)?)(?P<value>\S+)"),
    re.compile(r"(?P<head>^\s*snmp-server community\s+)(?P<value>\S+)"),
    # SNMPv3 user passwords, AAA server-private keys, and VPN keyring pre-shared keys
    re.compile(r"(?P<head>^\s*snmp-server user\b.*?\bauth\s+\S+\s+)(?P<value>\S+)"),
    re.compile(r"(?P<head>^\s*snmp-server user\b.*?\bpriv\s+(?:aes\s+\d+\s+|\S+\s+))(?P<value>\S+)"),
    re.compile(r"(?P<head>^\s*server-private\b.*?\bkey\s+(?:[0-9]\s+)?)(?P<value>\S+)"),
    re.compile(r"(?P<head>^\s*pre-shared-key\b.*?\bkey\s+(?:[0-9]\s+)?)(?P<value>\S+)"),
    re.compile(r"(?P<head>^\s*pre-shared-key\s+(?!address\b)(?:local\s+|remote\s+)?(?:[0-9]\s+)?)(?P<value>\S+)"),
]
MASK = "<removed>"
# The backup repo commits under its own name, and never asks for a signing key.
GIT_OPTIONS = ["-c", "user.name=catalyst-lifecycle", "-c", "user.email=catalyst-lifecycle@localhost"]
GIT_OPTIONS += ["-c", "commit.gpgsign=false"]


@dataclass(frozen=True)
class Backup:
    device: str
    status: str  # "first", "changed" or "unchanged"
    added: int = 0
    removed: int = 0
    diff: str = ""


def _mask(line: str) -> str:
    for pattern in SECRETS:
        line = pattern.sub(lambda m: m.group(0) if m.group("value") == MASK else m.group("head") + MASK, line)
    return line


def sanitize(config: str) -> str:
    lines = []
    for raw in config.replace("\r\n", "\n").split("\n"):
        line = raw.rstrip()
        if VOLATILE.match(line.strip()):
            continue
        lines.append(_mask(line))
    return "\n".join(lines).strip("\n") + "\n"


def _git(repo: Path, *args: str) -> str:
    git = shutil.which("git")
    if git is None:
        raise RuntimeError("git is not installed")
    command = [git, *GIT_OPTIONS, "-C", str(repo), *args]
    return subprocess.run(command, capture_output=True, text=True, check=True).stdout  # noqa: S603 (no shell)


def backup(device: str, config: str, repo: Path) -> Backup:
    """Write the sanitized config to <repo>/<device>.cfg and commit it if anything changed."""
    if not (repo / ".git").exists():
        repo.mkdir(parents=True, exist_ok=True)
        _git(repo, "init", "-q", "-b", "main")
    path = repo / f"{device}.cfg"
    first = not path.exists()
    path.write_text(sanitize(config))
    _git(repo, "add", path.name)
    numstat = _git(repo, "diff", "--cached", "--numstat", "--", path.name).split()
    if not numstat:
        return Backup(device, "unchanged")
    added, removed = int(numstat[0]), int(numstat[1])
    diff = _git(repo, "diff", "--cached", "--", path.name)
    message = f"{device}: first backup" if first else f"{device}: {added} added, {removed} removed"
    _git(repo, "commit", "-q", "-m", message)
    return Backup(device, "first" if first else "changed", added, removed, diff)
