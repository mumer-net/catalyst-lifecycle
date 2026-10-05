from pathlib import Path

from catalyst_lifecycle.parse import load_device, load_devices

CORPUS = Path(__file__).resolve().parents[1] / "corpus"


def test_inventory_lists_every_part_with_no_padding():
    device = load_device(CORPUS / "genie-c4507re-vss")
    assert len(device.parts) == 32
    first = device.parts[0]
    assert (first.name, first.pid, first.serial) == ("Switch1 System", "WS-C4507R+E", "FXS1941Q20T")
    assert first.description == "Cisco Systems, Inc. WS-C4507R+E 7 slot switch"
    assert all(p == p.strip() for part in device.parts for p in (part.name, part.pid, part.description))


def test_show_module_gives_the_chassis_and_each_module():
    device = load_device(CORPUS / "genie-c4507re-sup7le")
    assert [(p.name, p.pid) for p in device.parts] == [
        ("Chassis", "WS-C4507R+E"),
        ("Module 1", "WS-X4648-RJ45V+E"),
        ("Module 3", "WS-X45-SUP7L-E"),
        ("Module 6", "WS-X4648-RJ45V+E"),
        ("Module 7", "WS-X4648-RJ45V+E"),
    ]


def test_show_module_names_the_switch_in_a_vss():
    device = load_device(CORPUS / "ntc-c4507re-vss-standby")
    assert device.parts[3].name == "Switch 2 module 3"
    assert device.parts[3].pid == "WS-X45-SUP7-E"


def test_show_version_alone_gives_the_chassis():
    device = load_device(CORPUS / "genie-c4507r-ios-12.2")
    assert (device.hostname, device.version) == ("GENIE123123", "12.2(18)EW5")
    assert [(p.name, p.pid, p.serial) for p in device.parts] == [("Chassis", "WS-C4507R", "FOX093206HY")]


def test_load_devices_takes_a_folder_of_devices_or_one_device():
    devices = load_devices(CORPUS)
    assert len(devices) == 8
    assert sum(len(d.parts) for d in devices) == 60
    assert [d.name for d in load_devices(CORPUS / "genie-c9407r")] == ["genie-c9407r"]
