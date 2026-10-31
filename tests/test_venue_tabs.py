from tinseltown.model import COLUMNS
from tinseltown.sheet import plan_venue_tabs


def row(**cells):
    return [cells.get(c.split(" ")[0], "") for c in COLUMNS]


SCREENINGS = [
    COLUMNS,
    row(Venue="Vidiots", Title="Audition", Start="2026-10-30", Times="9:45 pm"),
    row(Venue="Vidiots", Title="Ran", Start="2026-11-02", Times="7:00 pm"),
    row(Venue="The New Beverly", Title="The Fly", Start="2026-10-30", Times="2:00 pm"),
]


def test_tabs_are_split_by_venue_newest_first():
    _, _, contents = plan_venue_tabs(SCREENINGS, {}, ["Vidiots", "The New Beverly", "Lumiere"])
    assert [r[3] for r in contents["Vidiots"][1:]] == ["Ran", "Audition"]
    assert len(contents["The New Beverly"]) == 2
    assert contents["Lumiere"] == [COLUMNS]  # empty tab, ready for entries


def test_edits_on_a_venue_tab_go_back_to_screenings():
    tab = [COLUMNS, row(Venue="Vidiots", Title="Audition", Start="2026-10-30", Times="9:45 pm", Seen="Yes")]
    edits, new_rows, contents = plan_venue_tabs(SCREENINGS, {"Vidiots": tab}, ["Vidiots"])
    assert edits == {(2, "Seen"): "Yes"}
    assert not new_rows
    assert contents["Vidiots"][2][COLUMNS.index("Seen")] == "Yes"


def test_rows_typed_on_a_venue_tab_are_added():
    tab = [COLUMNS, row(Title="Stalker", Start="2026-11-01")]
    _, new_rows, _ = plan_venue_tabs(SCREENINGS, {"Lumiere": tab}, ["Lumiere"])
    assert new_rows[0]["Venue"] == "Lumiere" and new_rows[0]["Status"] == "Manual"
