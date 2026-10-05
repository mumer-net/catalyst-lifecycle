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


class EolTable:
    def __init__(self, entries: list[Entry]):
        self.by_pid: dict[str, Entry] = {}
        for entry in entries:
            if entry.pid in self.by_pid:
                other = self.by_pid[entry.pid].notice.id
                raise ValueError(f"{entry.pid} is listed in both {other} and {entry.notice.id}")
            self.by_pid[entry.pid] = entry

    def find(self, pid: str) -> Entry | None:
        return self.by_pid.get(pid)


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


def lookup(pid: str, table: EolTable, as_of: date) -> Lookup:
    entry = table.find(pid)
    status = status_of(entry, as_of)
    if status == NOT_LISTED:
        return Lookup(pid, status)
    return Lookup(pid, status, entry, entry.replacement)
