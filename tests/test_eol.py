from datetime import date
from pathlib import Path

import pytest

from catalyst_lifecycle.eol import (
    ANNOUNCED,
    END_OF_SALE,
    NOT_LISTED,
    PAST_SUPPORT,
    Entry,
    EolTable,
    Lookup,
    Notice,
    load_table,
    lookup,
    status_of,
)

ROOT = Path(__file__).resolve().parents[1]
TABLE = load_table(ROOT / "data" / "eol.yaml")
AS_OF = date(2026, 9, 30)


def notice(id: str) -> Notice:
    return Notice(id, "Test", "https://www.cisco.com/", date(2020, 1, 1), date(2021, 1, 1), date(2022, 1, 1))


def test_every_notice_links_to_cisco():
    assert all(e.notice.url.startswith("https://www.cisco.com/") for e in TABLE.by_pid.values())


def test_status_changes_the_day_after_each_milestone():
    sup9 = TABLE.find("WS-X45-SUP9-E")  # end of sale 2021-10-30, last support 2026-10-31
    assert status_of(sup9, date(2021, 10, 30)) == ANNOUNCED
    assert status_of(sup9, date(2021, 10, 31)) == END_OF_SALE
    assert status_of(sup9, date(2026, 10, 31)) == END_OF_SALE
    assert status_of(sup9, date(2026, 11, 1)) == PAST_SUPPORT


def test_a_notice_announced_after_the_date_does_not_count_yet():
    assert lookup("C9400-SUP-1", TABLE, date(2024, 4, 29)).status == NOT_LISTED
    assert lookup("C9400-SUP-1", TABLE, date(2024, 4, 30)).status == ANNOUNCED


def test_sup8e_gets_the_replacement_its_notice_names():
    result = lookup("WS-X45-SUP8-E", TABLE, AS_OF)
    assert result.status == PAST_SUPPORT
    assert result.entry.notice.id == "EOL13217"
    assert result.replacement == "C9400-SUP-1XL"


def test_a_part_with_no_notice_is_not_listed():
    assert lookup("WS-X4590-EX=", TABLE, AS_OF) == Lookup("WS-X4590-EX=", NOT_LISTED)


def test_a_part_listed_twice_is_rejected():
    with pytest.raises(ValueError, match="listed in both"):
        EolTable([Entry("WS-X1", notice("EOL1"), None), Entry("WS-X1", notice("EOL1"), "WS-X2")])


def test_dates_out_of_order_are_rejected(tmp_path):
    bad = tmp_path / "eol.yaml"
    bad.write_text(
        "notices:\n"
        "  - {id: EOL1, title: t, url: u, announced: 2020-01-01, end_of_sale: 2019-01-01,"
        " last_support: 2025-01-01, parts: {WS-X1: null}}\n"
    )
    with pytest.raises(ValueError, match="out of order"):
        load_table(bad)
