from datetime import date
from pathlib import Path

import pytest

from catalyst_lifecycle.eol import load_table
from catalyst_lifecycle.measure import measure, read_key
from catalyst_lifecycle.parse import load_devices

ROOT = Path(__file__).resolve().parents[1]
TABLE = load_table(ROOT / "data" / "eol.yaml")
DEVICES = load_devices(ROOT / "corpus")


def test_the_key_covers_every_part_in_the_corpus():
    as_of, key = read_key(ROOT / "corpus" / "answer_key.csv")
    assert as_of == date(2026, 9, 30)
    score, rows = measure(DEVICES, TABLE, key, as_of)
    assert score.parts == len(rows) == 60


def test_a_key_that_disagrees_with_the_corpus_is_rejected():
    as_of, key = read_key(ROOT / "corpus" / "answer_key.csv")
    with pytest.raises(ValueError, match="disagree"):
        measure(DEVICES, TABLE, key[:-1], as_of)


def test_a_replacement_that_is_end_of_life_too_counts_as_stale():
    as_of, key = read_key(ROOT / "corpus" / "answer_key.csv")
    _, rows = measure(DEVICES, TABLE, key, as_of)
    sup7 = next(r for r in rows if r["pid"] == "WS-X45-SUP7-E")
    assert (sup7["replacement"], sup7["stale"]) == ("WS-X45-SUP8-E", "yes")
