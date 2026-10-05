"""catalyst-lifecycle: report on saved show output."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from rich.console import Console

from catalyst_lifecycle.eol import load_table
from catalyst_lifecycle.parse import load_devices
from catalyst_lifecycle.report import build_rows, print_report, write_csv, write_html

TABLE = Path("data/eol.yaml")
console = Console()


def cmd_report(args) -> int:
    rows = build_rows(load_devices(args.path), load_table(args.table), args.as_of)
    print_report(rows, args.as_of, console)
    if args.csv:
        write_csv(rows, args.csv)
    if args.html:
        write_html(rows, args.as_of, args.html)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="catalyst-lifecycle")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("report", help="look up every part in the end-of-life table")
    p.add_argument("path", type=Path, help="a device folder, or a folder of device folders")
    p.add_argument("--table", type=Path, default=TABLE)
    p.add_argument("--as-of", type=date.fromisoformat, default=date.today(), help="YYYY-MM-DD, default today")
    p.add_argument("--csv", type=Path)
    p.add_argument("--html", type=Path)
    p.set_defaults(func=cmd_report)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
