"""Look up Catalyst parts in Cisco's end-of-life notices.

data/eol.yaml is copied from Cisco's public notice pages. Cisco's EoX API only works for
support-contract customers and partners, so a table built from the notices is the way to
do this without one.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

PAST_SUPPORT = "past support"
END_OF_SALE = "end of sale"
ANNOUNCED = "announced"
NOT_LISTED = "not listed"

# Cisco adds these to a part number for a spare (=), a TAA-compliant spare (++=), or a second,
# redundant unit (/2). The hardware is the same, and some parts are only listed with one.
SUFFIXES = ("++=", "=", "/2")


@dataclass(frozen=True)
class Notice:
    id: str
    title: str
    url: str
    announced: date
    end_of_sale: date
    last_support: date


@dataclass(frozen=True)
class Entry:
    pid: str
    notice: Notice
    replacement: str | None


@dataclass(frozen=True)
class Lookup:
    pid: str
    status: str
    entry: Entry | None = None
    replacement: str | None = None
    chain: tuple[str, ...] = ()  # every replacement followed, the last one is the part to order


def base_pid(pid: str) -> str:
    pid = pid.strip().upper()
    for suffix in SUFFIXES:
        if pid.endswith(suffix):
            return pid[: -len(suffix)]
    return pid


class EolTable:
    def __init__(self, entries: list[Entry]):
        self.by_pid: dict[str, Entry] = {}
        self.by_base: dict[str, Entry] = {}
        for entry in entries:
            if entry.pid in self.by_pid:
                other = self.by_pid[entry.pid].notice.id
                raise ValueError(f"{entry.pid} is listed in both {other} and {entry.notice.id}")
            self.by_pid[entry.pid] = entry
            other = self.by_base.setdefault(base_pid(entry.pid), entry)
            if other.notice != entry.notice:
                raise ValueError(f"{entry.pid} and {other.pid} are the same part in two notices")

    def find(self, pid: str, exact: bool = False) -> Entry | None:
        return self.by_pid.get(pid) if exact else self.by_base.get(base_pid(pid))


def load_table(path: Path) -> EolTable:
    data = yaml.safe_load(path.read_text())
    entries = []
    for n in data["notices"]:
        notice = Notice(n["id"], n["title"], n["url"], n["announced"], n["end_of_sale"], n["last_support"])
        if not notice.announced <= notice.end_of_sale <= notice.last_support:
            raise ValueError(f"{notice.id}: dates are out of order")
        entries += [Entry(pid, notice, replacement) for pid, replacement in n["parts"].items()]
    return EolTable(entries)


def status_of(entry: Entry | None, as_of: date) -> str:
    # A notice dated after as_of didn't exist yet, so the part counts as not listed.
    if entry is None or as_of < entry.notice.announced:
        return NOT_LISTED
    if as_of > entry.notice.last_support:
        return PAST_SUPPORT
    if as_of > entry.notice.end_of_sale:
        return END_OF_SALE
    return ANNOUNCED


def lookup(pid: str, table: EolTable, as_of: date, follow: bool = True, exact: bool = False) -> Lookup:
    """Find the part and, by default, follow replacements until one has no end-of-life notice.

    follow=False and exact=True give the v0.1 lookup: the exact part number, and the
    replacement the first notice names even when that part is end-of-life too.
    """
    entry = table.find(pid, exact)
    status = status_of(entry, as_of)
    if status == NOT_LISTED:
        return Lookup(pid, status)
    chain: list[str] = []
    current = entry
    while current.replacement:
        part = current.replacement
        if part in chain:
            raise ValueError(f"replacement loop for {pid}: {' > '.join([*chain, part])}")
        chain.append(part)
        nxt = table.find(part, exact)
        if not follow or status_of(nxt, as_of) == NOT_LISTED:
            return Lookup(pid, status, entry, part, tuple(chain))
        current = nxt
    # The chain ends at a part that is end-of-life and names no replacement.
    return Lookup(pid, status, entry, None, tuple(chain))
