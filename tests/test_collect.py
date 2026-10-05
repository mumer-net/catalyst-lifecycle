from pathlib import Path

import pytest

from catalyst_lifecycle import collect as collect_module
from catalyst_lifecycle.collect import Target, collect, load_targets

ROOT = Path(__file__).resolve().parents[1]


class FakeHandler:
    """Stands in for Netmiko's ConnectHandler and answers each command with its own name."""

    def __init__(self, **params):
        self.params = params

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def send_command(self, command, **kwargs):
        return f"output of {command}"


def test_devices_file_names_env_vars_and_holds_no_credentials():
    targets = load_targets(ROOT / "devices.yaml")
    assert targets
    assert all(t.username_env and t.password_env for t in targets)
    assert "password:" not in (ROOT / "devices.yaml").read_text()


def test_collect_needs_credentials_in_the_environment(tmp_path, monkeypatch):
    monkeypatch.delenv("SANDBOX_USERNAME", raising=False)
    with pytest.raises(RuntimeError, match="set SANDBOX_USERNAME"):
        collect(Target("lab", "192.0.2.1"), tmp_path)


def test_collect_saves_one_file_per_command(tmp_path, monkeypatch):
    monkeypatch.setenv("SANDBOX_USERNAME", "user")
    monkeypatch.setenv("SANDBOX_PASSWORD", "pass")
    monkeypatch.setattr(collect_module, "ConnectHandler", FakeHandler)
    folder = collect(Target("lab", "192.0.2.1"), tmp_path)
    assert sorted(p.name for p in folder.iterdir()) == [
        "show_inventory.txt",
        "show_running-config.txt",
        "show_version.txt",
    ]
    assert (folder / "show_inventory.txt").read_text() == "output of show inventory\n"
