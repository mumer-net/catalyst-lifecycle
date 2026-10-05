from catalyst_lifecycle.backup import _git, backup, sanitize

CONFIG = """Building configuration...

Current configuration : 6328 bytes
!
! Last configuration change at 14:02:11 UTC Wed Sep 30 2026 by developer
! NVRAM config last updated at 13:55:40 UTC Wed Sep 30 2026 by developer
!
version 17.15
hostname edge-1
!
enable secret 9 $9$abcdefghijklmn$opqrstuvwxyz0123456789ABCDEFGHIJKLMNOPQRSTU
username developer privilege 15 secret 9 $9$zyxwvutsrqponm$lkjihgfedcba9876543210ZYXWVUTSRQPONMLKJIHGF
service password-encryption
snmp-server community s3cret-ro RO
tacacs-server host 192.0.2.10 key 7 0822455D0A16
snmp-server user monitor v3group v3 auth sha v3-auth-pass priv aes 128 v3-priv-pass
!
aaa group server tacacs+ admins
 server-private 192.0.2.11 key 7 1511021F0725
!
crypto keyring branch-vpn
  pre-shared-key address 198.51.100.7 key psk-branch-1
crypto ikev2 keyring hub-vpn
 peer branch
  pre-shared-key psk-branch-2
ntp clock-period 17179869
!
key chain ospf-keys
 key 1
  key-string 7 045802150C2E
!
interface Loopback0
 description uplink to core
 ip ospf message-digest-key 1 md5 7 13061E010803
!
line vty 0 4
 password 7 060506324F41
!
end
"""


def test_sanitize_drops_lines_that_change_on_every_read():
    clean = sanitize(CONFIG)
    for volatile in ("Building configuration", "Current configuration", "Last configuration change", "NVRAM", "clock"):
        assert volatile not in clean
    assert clean.startswith("!\n!\nversion 17.15")


def test_sanitize_masks_every_secret_and_keeps_the_rest():
    clean = sanitize(CONFIG)
    for secret in ("$9$", "s3cret-ro", "0822455D0A16", "045802150C2E", "13061E010803", "060506324F41"):
        assert secret not in clean
    for secret in ("v3-auth-pass", "v3-priv-pass", "1511021F0725", "psk-branch-1", "psk-branch-2"):
        assert secret not in clean
    assert "enable secret 9 <removed>" in clean
    assert "username developer privilege 15 secret 9 <removed>" in clean
    assert "snmp-server community <removed> RO" in clean
    assert "tacacs-server host 192.0.2.10 key 7 <removed>" in clean
    assert "snmp-server user monitor v3group v3 auth sha <removed> priv aes 128 <removed>" in clean
    assert "pre-shared-key address 198.51.100.7 key <removed>" in clean
    assert " key 1\n" in clean  # a key number, not a secret
    assert "service password-encryption" in clean
    assert sanitize(clean) == clean


def test_backup_commits_only_when_the_config_changes(tmp_path):
    repo = tmp_path / "backups"
    assert backup("edge-1", CONFIG, repo).status == "first"
    # a new timestamp alone is not a change
    later = CONFIG.replace("14:02:11", "18:40:02")
    assert backup("edge-1", later, repo).status == "unchanged"

    changed = backup("edge-1", later.replace("uplink to core", "uplink to core-2"), repo)
    assert (changed.status, changed.added, changed.removed) == ("changed", 1, 1)
    assert "+ description uplink to core-2" in changed.diff

    log = _git(repo, "log", "--format=%s").splitlines()
    assert log == ["edge-1: 1 added, 1 removed", "edge-1: first backup"]
    assert "$9$" not in _git(repo, "show", "HEAD~1:edge-1.cfg")
