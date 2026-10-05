# Drills

I ran these by hand on the DevNet Catalyst 8000V always-on sandbox in October 2026. The output below is copied from my terminal. The sandbox is shared, so I left out every line that belongs to other users.

## First SSH by hand

Before writing any collection code, I logged in with plain `ssh` and ran `show version` and `show inventory`.

```text
Cisco IOS XE Software, Version 17.15.04c
PID: C8000V            , VID: V00  , SN: ...
```

There are spaces after the VID value, before the comma. ntc-templates keeps them in its parsed output (`'V00  '`), which is why the parser strips every field. One of the three inventory entries (module F0) has an empty VID and serial, and it still parses.

My first login attempt closed right after the password prompt. The password hadn't pasted cleanly. The second try worked.

## Drill 2: one device is down

My DevNet account allows one active sandbox at a time, so I couldn't break a second sandbox. Instead I added a second device at 192.0.2.1, an address reserved for documentation that nothing answers on, and ran `collect` with both.

```text
devnet-cat8000v: saved to captures/devnet-cat8000v
dead-switch: TCP connection to device failed.
...
Device settings: cisco_xe 192.0.2.1:22

real    0m23.507s
exit code 1
```

The 8000V saved as usual. The dead device took about 20 seconds to fail (the connection timeout), printed in red, and the run exited with code 1 so a scheduler would notice. At 200 switches, 20 seconds per dead device in a serial loop adds up, which is why collecting in parallel is on my list.

## Drill 3: a change the backup has to catch

This is the only time I changed the device. I added a loopback with a number nobody else was likely to use, backed up, removed it, and backed up again.

```text
devnet-cat8000v: changed, 4 added, 0 removed
+interface Loopback4507
+ description catalyst-lifecycle backup drill
+ no ip address
+!
```

I never typed `no ip address`. The device adds it to a new interface on its own, and the backup caught that too. After I removed the loopback, the next backup showed the same four lines with `-`. The backup repo history:

```text
8dcf23a devnet-cat8000v: 0 added, 4 removed
fd4f32e devnet-cat8000v: 4 added, 0 removed
352ac93 devnet-cat8000v: first backup
```

No one else changed the sandbox config in the few minutes between the three backups, so those were the only diffs.

## Secret check on the first backup

After the first backup I searched it for anything that looked like a secret and wasn't masked:

```text
6:service password-encryption
39:aaa common-criteria policy PASSWORD_POLICY
78: rsakeypair TP-self-signed-...
```

All three are names, not secrets.
