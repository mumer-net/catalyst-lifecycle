from pathlib import Path

from catalyst_lifecycle.cli import main

ROOT = Path(__file__).resolve().parents[1]


def test_report_writes_csv_and_html(tmp_path, monkeypatch):
    monkeypatch.chdir(ROOT)
    csv_file, html_file = tmp_path / "r.csv", tmp_path / "r.html"
    assert main(["report", "corpus", "--as-of", "2026-09-30", "--csv", str(csv_file), "--html", str(html_file)]) == 0
    assert len(csv_file.read_text().splitlines()) == 61  # header and 60 parts
    assert "Replacement parts" in html_file.read_text()
