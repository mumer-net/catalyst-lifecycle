import csv
from datetime import date
from pathlib import Path

from catalyst_lifecycle.eol import load_table
from catalyst_lifecycle.parse import Device, Part
from catalyst_lifecycle.report import build_rows, refresh_list, summary, write_csv, write_html

TABLE = load_table(Path(__file__).resolve().parents[1] / "data" / "eol.yaml")
AS_OF = date(2026, 9, 30)


def device(*pids: str) -> Device:
    return Device(
        "lab", parts=[Part("lab", f"part {i}", pid, f"SN{i}", "", "show inventory") for i, pid in enumerate(pids)]
    )


def test_summary_counts_each_status():
    rows = build_rows([device("WS-C4507R+E", "C9400-SUP-1", "SFP-10G-SR")], TABLE, AS_OF)
    assert summary(rows) == "1 past support, 1 end of sale, 0 announced, 1 not listed"


def test_refresh_list_counts_each_replacement():
    rows = build_rows([device("PWR-C45-2800ACV", "PWR-C45-2800ACV", "WS-C4506-E", "SFP-10G-SR")], TABLE, AS_OF)
    assert refresh_list(rows) == [("C9400-PWR-3200AC", 2), ("C9407R", 1)]


def test_csv_has_one_row_per_part(tmp_path):
    out = tmp_path / "report.csv"
    write_csv(build_rows([device("WS-C4507R+E", "SFP-10G-SR")], TABLE, AS_OF), out)
    rows = list(csv.DictReader(out.open()))
    assert [r["pid"] for r in rows] == ["WS-C4507R+E", "SFP-10G-SR"]
    assert rows[0]["notice"] == "EOL13217"
    assert rows[0]["last_support"] == "2025-10-31"
    assert rows[0]["replace_with"] == "C9407R"
    assert rows[1]["status"] == "not listed"


def test_html_escapes_what_it_prints(tmp_path):
    out = tmp_path / "report.html"
    write_html(build_rows([device("<script>")], TABLE, AS_OF), AS_OF, out)
    page = out.read_text()
    assert "&lt;script&gt;" in page
    assert "<script>" not in page
