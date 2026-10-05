import json
from pathlib import Path

from catalyst_lifecycle.cli import main

ROOT = Path(__file__).resolve().parents[1]


def test_report_writes_csv_and_html(tmp_path, monkeypatch):
    monkeypatch.chdir(ROOT)
    csv_file, html_file = tmp_path / "r.csv", tmp_path / "r.html"
    assert main(["report", "corpus", "--as-of", "2026-09-30", "--csv", str(csv_file), "--html", str(html_file)]) == 0
    assert len(csv_file.read_text().splitlines()) == 61  # header and 60 parts
    assert "Replacement parts" in html_file.read_text()


def test_measure_writes_rows_and_a_summary(tmp_path, monkeypatch):
    monkeypatch.chdir(ROOT)
    out = tmp_path / "results" / "run.csv"
    assert main(["measure", "--out", str(out)]) == 0
    assert len(out.read_text().splitlines()) == 61
    summary = json.loads(out.with_suffix(".json").read_text())
    assert summary["as_of"] == "2026-09-30"
    assert summary["parts"] == 60


def test_backup_reads_saved_running_configs(tmp_path):
    device = tmp_path / "captures" / "edge-1"
    device.mkdir(parents=True)
    (device / "show_running-config.txt").write_text("hostname edge-1\nenable secret 9 $9$abc\nend\n")
    repo = tmp_path / "backups"
    assert main(["backup", str(tmp_path / "captures"), "--repo", str(repo)]) == 0
    assert (repo / "edge-1.cfg").read_text() == "hostname edge-1\nenable secret 9 <removed>\nend\n"
