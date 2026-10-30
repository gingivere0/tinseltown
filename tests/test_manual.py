from tinseltown.sheet import MANUAL_COLUMNS, ManualSheet


class FakeWorksheet:
    def __init__(self, values):
        self.values = values
        self.appended, self.updates = [], []

    def get_all_values(self):
        return self.values

    def append_rows(self, rows, **_):
        self.appended += rows

    def batch_update(self, updates):
        self.updates += updates


class FakeTracker:
    def __init__(self):
        self.rows = []

    def append_new(self, rows):
        self.rows += rows
        return len(rows)


def manual_sheet(values, venues=()):
    sheet = ManualSheet.__new__(ManualSheet)
    sheet.tracker = FakeTracker()
    sheet.ws = FakeWorksheet(values)
    sheet._chains = lambda: dict(venues)
    return sheet


def row(**cells):
    return [cells.get(c.replace(" ", "_").replace("'", ""), "") for c in MANUAL_COLUMNS]


def test_add_week_skips_venues_already_listed():
    sheet = manual_sheet([MANUAL_COLUMNS, row(Week_of="2026-10-30", Venue="Lumiere")])
    added = sheet.add_week("2026-10-30", [("Lumiere", "https://l", "x"), ("Whammy", "https://w", "y")])
    assert added == 1
    assert sheet.ws.appended[0][:4] == ["'2026-10-30", "'Whammy", "'https://w", "'y"]


def test_sync_copies_filled_rows_once():
    sheet = manual_sheet([
        MANUAL_COLUMNS,
        row(Week_of="2026-10-30", Venue="Lumiere", Title="Ran", Times="7:00 pm"),
        row(Week_of="2026-10-30", Venue="Whammy"),
        row(Week_of="2026-10-30", Venue="Lumiere", Title="Kagemusha", Added_to_Screenings="Yes"),
    ], venues={"Lumiere": "Lumiere Cinema"})
    assert sheet.sync() == 1
    copied = sheet.tracker.rows[0]
    assert copied["Title"] == "Ran" and copied["Status"] == "Manual"
    assert copied["Start date"] == copied["End date"] == "2026-10-30"
    assert copied["Chain or group"] == "Lumiere Cinema"
    assert sheet.ws.updates == [{"range": "Q2", "values": [["Yes"]]}]
