from tinseltown.export import SITE_COLUMNS, build

SCREENINGS = [
    ["Venue", "Chain or group", "Title", "Year", "Director", "Start date", "End date", "Times", "Seen", "Status", "Source file"],
    ["The New Beverly", "New Beverly", "The Fly", "1986", "", "2026-10-30", "2026-10-30", "2:00 pm", "Yes", "Auto",
     "https://thenewbev.com/program/the-fly/"],
    ["The Aero", "American Cinematheque", "Duck Soup", "", "", "1/1/2026", "", "4:00 pm", "", "Imported", "AC 2026.numbers"],
    ["The Aero", "American Cinematheque", "", "", "", "2026-01-02", "", "", "", "", ""],
    ["The Aero", "American Cinematheque", "No Date", "", "", "", "", "", "", "", ""],
]
FILMS = [["Title", "Year", "Director", "Runtime (min)"], ["duck soup", "1933", "Leo McCarey", "69"], ["Untouched", "", "", ""]]
VENUES = [["Venue", "Chain or group", "Status"], ["The Aero", "American Cinematheque", "Open"]]


def test_build_keeps_dated_rows_and_fills_in_from_films():
    data = build(SCREENINGS, FILMS, VENUES, "2026-10-31T00:00+00:00")
    rows = [dict(zip(data["columns"], r)) for r in data["rows"]]
    assert data["columns"] == SITE_COLUMNS
    assert [r["Title"] for r in rows] == ["The Fly", "Duck Soup"]
    fly, soup = rows
    assert fly["Link"] == "https://thenewbev.com/program/the-fly/" and fly["Year"] == "1986"
    assert soup["Start date"] == soup["End date"] == "2026-01-01"
    assert (soup["Year"], soup["Director"], soup["Link"]) == ("1933", "Leo McCarey", "")
    assert "Seen" not in data["columns"]
    assert data["films"] == {"duck soup": {"year": "1933", "director": "Leo McCarey", "runtime": "69"}}
    assert data["venues"] == [{"venue": "The Aero", "chain": "American Cinematheque", "status": "Open"}]
