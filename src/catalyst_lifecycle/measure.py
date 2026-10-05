"""Score the lookup against the answer key in corpus/answer_key.csv.

The key gives the status and the part to order for every part in the corpus, on one fixed
date (its as_of column), read off Cisco's notices. A replacement counts as stale when the
notices say it is end-of-life too, so ordering it would be a mistake.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from catalyst_lifecycle.eol import NOT_LISTED, EolTable, lookup, status_of
from catalyst_lifecycle.parse import Device


@dataclass
class Score:
    parts: int = 0
    status_right: int = 0
    with_replacement: int = 0  # parts the key names a replacement for
    replacement_right: int = 0
    stale: int = 0


def read_key(path: Path) -> tuple[date, list[dict[str, str]]]:
    key = list(csv.DictReader(path.read_text().splitlines()))
    dates = {k["as_of"] for k in key}
    if len(dates) != 1:
        raise ValueError(f"the key should have one as_of date, found {sorted(dates)}")
    return date.fromisoformat(dates.pop()), key


def measure(devices: list[Device], table: EolTable, key: list[dict[str, str]], as_of: date):
    parts = {(p.device, p.name): p for device in devices for p in device.parts}
    keyed = {(k["device"], k["name"]) for k in key}
    if keyed != set(parts):
        raise ValueError(f"key and corpus disagree: {sorted(keyed ^ set(parts))}")

    score, rows = Score(), []
    for k in key:
        part = parts[(k["device"], k["name"])]
        result = lookup(part.pid, table, as_of)
        replacement = result.replacement or ""
        stale = bool(replacement) and status_of(table.find(replacement), as_of) != NOT_LISTED
        score.parts += 1
        score.status_right += result.status == k["status"]
        if k["replacement"]:
            score.with_replacement += 1
            score.replacement_right += replacement == k["replacement"]
        score.stale += stale
        rows.append(
            {
                "device": part.device,
                "name": part.name,
                "pid": part.pid,
                "expected_status": k["status"],
                "status": result.status,
                "expected_replacement": k["replacement"],
                "replacement": replacement,
                "stale": "yes" if stale else "",
            }
        )
    return score, rows


def write_rows(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
