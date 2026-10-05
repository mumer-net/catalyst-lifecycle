"""catalyst-lifecycle: collect, back up, report, and measure."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from catalyst_lifecycle import backup as backups
from catalyst_lifecycle.collect import collect, load_targets
from catalyst_lifecycle.eol import load_table
from catalyst_lifecycle.measure import measure, read_key, write_rows
from catalyst_lifecycle.parse import command_file, load_devices
from catalyst_lifecycle.report import build_rows, print_report, write_csv, write_html

TABLE = Path("data/eol.yaml")
console = Console()


def cmd_collect(args) -> int:
    load_dotenv(".env")
    failed = 0
    for target in load_targets(args.devices):
        try:
            folder = collect(target, args.out)
        except Exception as e:  # one unreachable device shouldn't stop the rest
            console.print(f"{target.name}: {e}", style="red", markup=False)
            failed += 1
            continue
        console.print(f"{target.name}: saved to {folder}")
    return 1 if failed else 0


def cmd_backup(args) -> int:
    repo = args.repo.expanduser()
    for config_file in sorted(args.captures.glob("*/" + command_file("show running-config"))):
        device = config_file.parent.name
        result = backups.backup(device, config_file.read_text(), repo)
        if result.status == "changed":
            console.print(f"{device}: changed, {result.added} added, {result.removed} removed")
            console.print(result.diff, markup=False, highlight=False)
        else:
            console.print(f"{device}: {result.status}")
    return 0


def cmd_report(args) -> int:
    rows = build_rows(load_devices(args.path), load_table(args.table), args.as_of)
    print_report(rows, args.as_of, console)
    if args.csv:
        write_csv(rows, args.csv)
    if args.html:
        write_html(rows, args.as_of, args.html)
    return 0


def cmd_measure(args) -> int:
    as_of, key = read_key(args.key)
    score, rows = measure(load_devices(args.corpus), load_table(args.table), key, as_of)
    table = Table(title=f"Answer key, {score.parts} parts, as of {as_of}")
    table.add_column("What")
    table.add_column("Result", justify="right")
    table.add_row("Status right", f"{score.status_right}/{score.parts}")
    table.add_row("Replacement right", f"{score.replacement_right}/{score.with_replacement}")
    table.add_row("Replacements that are end-of-life too", str(score.stale))
    console.print(table)
    if args.out:
        write_rows(rows, args.out)
        summary = {"as_of": str(as_of), "lookup": "exact part number, one hop", **asdict(score)}
        args.out.with_suffix(".json").write_text(json.dumps(summary, indent=2) + "\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="catalyst-lifecycle")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("collect", help="save show output from each device in devices.yaml (read-only)")
    p.add_argument("--devices", type=Path, default=Path("devices.yaml"))
    p.add_argument("--out", type=Path, default=Path("captures"))
    p.set_defaults(func=cmd_collect)

    p = sub.add_parser("backup", help="commit each device's running config to a local Git repo")
    p.add_argument("captures", type=Path, nargs="?", default=Path("captures"))
    p.add_argument("--repo", type=Path, default=Path("~/config-backups"))
    p.set_defaults(func=cmd_backup)

    p = sub.add_parser("report", help="look up every part in the end-of-life table")
    p.add_argument("path", type=Path, help="a device folder, or a folder of device folders")
    p.add_argument("--table", type=Path, default=TABLE)
    p.add_argument("--as-of", type=date.fromisoformat, default=date.today(), help="YYYY-MM-DD, default today")
    p.add_argument("--csv", type=Path)
    p.add_argument("--html", type=Path)
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("measure", help="score the lookup against the answer key")
    p.add_argument("--corpus", type=Path, default=Path("corpus"))
    p.add_argument("--key", type=Path, default=Path("corpus/answer_key.csv"))
    p.add_argument("--table", type=Path, default=TABLE)
    p.add_argument("--out", type=Path, help="write per-part results here (CSV) and a summary next to it (JSON)")
    p.set_defaults(func=cmd_measure)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
