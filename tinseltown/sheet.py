"""Append new screenings to the Screenings tab of the tracker sheet."""
import json

import gspread
import gspread.utils
from google.oauth2.service_account import Credentials

from .model import COLUMNS


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
TAB = "Screenings"


def _key(venue: str, title: str, start: str, times: str) -> tuple:
    return (venue.lower().strip(), title.lower().strip(), start.strip(), times.lower().strip())


# Columns Sheets should parse (dates for the week filters, year as a number).
PARSED = {"Start date", "End date", "Year"}


def _cell(col: str, value: str) -> str:
    # Everything else goes in as text, so "7:30 pm" stays a time label rather
    # than a day fraction and titles like "=Equals" or "1917" aren't reinterpreted.
    if col in PARSED or not value:
        return value
    return "'" + value


class TrackerSheet:
    def __init__(self, sheet_id: str, service_account_json: str):
        creds = Credentials.from_service_account_info(json.loads(service_account_json), scopes=SCOPES)
        self.ws = gspread.authorize(creds).open_by_key(sheet_id).worksheet(TAB)

    def append_new(self, rows: list[dict]) -> int:
        existing = self.ws.get_all_values()
        header = existing[0]
        idx = {name: header.index(name) for name in ("Venue", "Title", "Start date", "Times")}
        seen = {
            _key(*(r[idx[c]] if idx[c] < len(r) else "" for c in ("Venue", "Title", "Start date", "Times")))
            for r in existing[1:]
        }
        new = []
        for row in rows:
            k = _key(row["Venue"], row["Title"], row["Start date"], row["Times"])
            if k in seen:
                continue
            seen.add(k)
            new.append([_cell(col, str(row.get(col, ""))) for col in header])
        if new:
            self.ws.append_rows(new, value_input_option="USER_ENTERED", table_range="A1")
            self._cover_all_rows()
        return len(new)

    def _cover_all_rows(self):
        # Keep the header filter and saved filter views (like "This week")
        # stretched over every row, including the ones just appended.
        sheet_id = self.ws.id
        meta = self.ws.spreadsheet.fetch_sheet_metadata({"fields": "sheets(properties(sheetId,gridProperties),basicFilter,filterViews)"})
        sheet = next(s for s in meta["sheets"] if s["properties"]["sheetId"] == sheet_id)
        grid = sheet["properties"]["gridProperties"]
        whole = {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": grid["rowCount"],
                 "startColumnIndex": 0, "endColumnIndex": grid["columnCount"]}
        # Re-set the header filter with whatever sort or filter is already on it.
        basic = dict(sheet.get("basicFilter", {}), range=whole)
        basic.pop("criteria", None)
        requests = [{"setBasicFilter": {"filter": basic}}]
        for view in sheet.get("filterViews", []):
            requests.append({"updateFilterView": {"filter": {"filterViewId": view["filterViewId"], "range": whole},
                                                  "fields": "range"}})
        self.ws.spreadsheet.batch_update({"requests": requests})


MANUAL_TAB = "Manual"
MANUAL_COLUMNS = [
    "Week of", "Venue", "Website", "Why it's manual", "Title", "Screen", "Year", "Director",
    "Start date", "End date", "Dates (as listed)", "Times", "Format", "Events", "Series", "Notes",
    "Added to Screenings",
]


class ManualSheet:
    """The Manual tab: one placeholder row per venue the job couldn't read each week.
    Jonathan fills in titles (adding rows for more films), and sync() copies the
    finished rows into Screenings with Status "Manual"."""

    def __init__(self, tracker: TrackerSheet):
        self.tracker = tracker
        self.ws = tracker.ws.spreadsheet.worksheet(MANUAL_TAB)

    def add_week(self, week_of: str, venues: list[tuple[str, str, str]]) -> int:
        """venues: (name, website, reason). Skips venues already listed for that week."""
        existing = self.ws.get_all_values()
        header = existing[0]
        have = {(r[header.index("Week of")], r[header.index("Venue")]) for r in existing[1:] if len(r) > 1}
        rows = []
        for name, url, why in venues:
            if (week_of, name) in have:
                continue
            values = {"Week of": week_of, "Venue": name, "Website": url, "Why it's manual": why}
            rows.append([_cell(c, values.get(c, "")) for c in header])
        if rows:
            self.ws.append_rows(rows, value_input_option="USER_ENTERED", table_range="A1")
        return len(rows)

    def _chains(self) -> dict[str, str]:
        rows = self.ws.spreadsheet.worksheet("Venues").get_all_values()[1:]
        return {r[0]: r[1] for r in rows if len(r) > 1}

    def sync(self) -> int:
        """Copy filled-in rows (those with a title) into Screenings, then mark them added."""
        chains = self._chains()
        values = self.ws.get_all_values()
        header = values[0]
        col = {name: i for i, name in enumerate(header)}
        get = lambda r, name: r[col[name]].strip() if col.get(name, len(r)) < len(r) else ""
        rows, marks = [], []
        for n, r in enumerate(values[1:], start=2):
            if not get(r, "Title") or get(r, "Added to Screenings"):
                continue
            start = get(r, "Start date") or get(r, "Week of")
            row = {c: get(r, c) for c in header if c in COLUMNS}
            row.update({
                "Chain or group": chains.get(get(r, "Venue"), get(r, "Venue")),
                "Start date": start,
                "End date": get(r, "End date") or start,
                "Status": "Manual",
                "Source file": get(r, "Website"),
            })
            rows.append(row)
            marks.append(n)
        if not rows:
            return 0
        self.tracker.append_new(rows)
        mark_col = gspread.utils.rowcol_to_a1(1, col["Added to Screenings"] + 1).rstrip("1")
        self.ws.batch_update([{"range": f"{mark_col}{n}", "values": [["Yes"]]} for n in marks])
        return len(rows)
