import datetime as dt

from tinseltown.model import Screening, format_dates
from tinseltown import normalize

D = dt.date


def test_single_day():
    assert format_dates([D(2026, 1, 1)]) == "01.01 Thurs"


def test_consecutive_run():
    assert format_dates([D(2026, 1, 13), D(2026, 1, 14), D(2026, 1, 15)]) == "01.13 Tues - 01.15 Thurs"


def test_scattered_dates():
    assert format_dates([D(2026, 1, 9), D(2026, 1, 2)]) == "01.02 Fri, 01.09 Fri"


def test_weekly_block():
    assert format_dates([D(2026, 1, 2), D(2026, 1, 5)], weekly=True) == "01.02 - 01.09"


def test_formats_map_to_fixed_list():
    assert normalize.formats("IMAX, DOLBY, PRIME, XL") == ["IMAX", "Dolby Cinema", "PRIME", "XL"]
    assert normalize.formats("4k") == ["4K DCP"]
    assert normalize.formats("VA, 16mm") == ["16mm"]


def test_events_from_notes():
    assert normalize.events("Q&A with Warwick Thornton\nDF w/ The Stranger") == ["Q&A", "Double feature"]


def test_row_shape():
    s = Screening(venue="The New Beverly", chain="The New Beverly", title="Night Moves",
                  dates=[D(2026, 1, 13), D(2026, 1, 15)], times="9:50 pm")
    row = s.row()
    assert row["Start date"] == "2026-01-13" and row["End date"] == "2026-01-15"
    assert row["Dates (as listed)"] == "01.13 Tues, 01.15 Thurs"
    assert row["Status"] == "Auto"
