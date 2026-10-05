"""Report each part's lifecycle status as a terminal table, a CSV file, and an HTML page."""

from __future__ import annotations

import csv
import html
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.text import Text

from catalyst_lifecycle.eol import ANNOUNCED, END_OF_SALE, NOT_LISTED, PAST_SUPPORT, EolTable, Lookup, lookup
from catalyst_lifecycle.parse import Device, Part

STATUSES = (PAST_SUPPORT, END_OF_SALE, ANNOUNCED, NOT_LISTED)
STYLES = {PAST_SUPPORT: "red", END_OF_SALE: "yellow", ANNOUNCED: "cyan", NOT_LISTED: "dim"}
COLUMNS = ("device", "name", "pid", "serial", "status", "notice", "matched_as", "end_of_sale", "last_support")
COLUMNS += ("replace_with", "via")


@dataclass(frozen=True)
class Row:
    part: Part
    result: Lookup

    def values(self) -> dict[str, str]:
        entry, result = self.result.entry, self.result
        # the replacements passed through on the way to the one to order
        via = result.chain[:-1] if result.replacement else result.chain
        return {
            "device": self.part.device,
            "name": self.part.name,
            "pid": self.part.pid,
            "serial": self.part.serial,
            "status": result.status,
            "notice": entry.notice.id if entry else "",
            "matched_as": entry.pid if entry and entry.pid != self.part.pid else "",
            "end_of_sale": str(entry.notice.end_of_sale) if entry else "",
            "last_support": str(entry.notice.last_support) if entry else "",
            "replace_with": result.replacement or "",
            "via": " > ".join(via),
        }


def build_rows(devices: list[Device], table: EolTable, as_of: date) -> list[Row]:
    return [Row(part, lookup(part.pid, table, as_of)) for device in devices for part in device.parts]


def counts(rows: list[Row]) -> Counter:
    return Counter(row.result.status for row in rows)


def refresh_list(rows: list[Row]) -> list[tuple[str, int]]:
    """What the notices say to order for everything no longer sold, one for one."""
    wanted = Counter(
        row.result.replacement
        for row in rows
        if row.result.status in (PAST_SUPPORT, END_OF_SALE) and row.result.replacement
    )
    return sorted(wanted.items())


def summary(rows: list[Row]) -> str:
    found = counts(rows)
    return ", ".join(f"{found[status]} {status}" for status in STATUSES)


def print_report(rows: list[Row], as_of: date, console: Console) -> None:
    table = Table(title=f"Lifecycle status on {as_of}")
    for heading in ("Device", "Part", "PID", "Status", "Support ends", "Replace with", "Via"):
        table.add_column(heading)
    for row in rows:
        v = row.values()
        status = Text(v["status"], style=STYLES[v["status"]])
        table.add_row(v["device"], v["name"], v["pid"], status, v["last_support"], v["replace_with"], v["via"])
    console.print(table)
    console.print(summary(rows))


def write_csv(rows: list[Row], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(row.values() for row in rows)


def write_html(rows: list[Row], as_of: date, path: Path) -> None:
    def cells(values, tag="td"):
        return "".join(f"<{tag}>{html.escape(str(v))}</{tag}>" for v in values)

    parts = "\n".join(
        f'<tr class="{row.result.status.replace(" ", "-")}">{cells(row.values()[c] for c in COLUMNS)}</tr>'
        for row in rows
    )
    order = "\n".join(f"<tr>{cells((pid, count))}</tr>" for pid, count in refresh_list(rows))
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Lifecycle status on {as_of}</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #1a1a1a; }}
  table {{ border-collapse: collapse; margin-bottom: 2rem; }}
  th, td {{ border: 1px solid #ccc; padding: 4px 8px; text-align: left; font-size: 14px; }}
  tr.past-support td:nth-child(5) {{ color: #b00020; font-weight: 600; }}
  tr.end-of-sale td:nth-child(5) {{ color: #8a5a00; font-weight: 600; }}
  tr.not-listed td {{ color: #777; }}
</style>
</head>
<body>
<h1>Lifecycle status on {as_of}</h1>
<p>{html.escape(summary(rows))}</p>
<h2>Replacement parts, one for one</h2>
<table>
<tr>{cells(("Part", "Quantity"), "th")}</tr>
{order}
</table>
<h2>Every part</h2>
<table>
<tr>{cells(COLUMNS, "th")}</tr>
{parts}
</table>
</body>
</html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(page)
