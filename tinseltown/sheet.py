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


# Tabs that aren't per-venue copies; refresh() never touches these.
CORE_TABS = {TAB, MANUAL_TAB, "Films", "Venues"}


def plan_venue_tabs(screenings: list[list[str]], tabs: dict[str, list[list[str]]], venues: list[str]):
    """Work out what refresh() should do, without touching the sheet.

    screenings: the Screenings tab (header first). tabs: current per-venue tabs by name.
    Returns (edits, new_rows, contents):
      edits     {(screenings row number, column name): value} for cells changed on a venue tab
      new_rows  rows typed into a venue tab that aren't in Screenings yet (as dicts)
      contents  {venue: rows to write to its tab, newest first, header included}
    """
    header = screenings[0]
    col = {name: i for i, name in enumerate(header)}
    pad = lambda r: r + [""] * (len(header) - len(r))
    key = lambda r: _key(r[col["Venue"]], r[col["Title"]], r[col["Start date"]], r[col["Times"]])
    rows = [pad(r) for r in screenings[1:]]
    where = {key(r): n for n, r in enumerate(rows)}

    edits, new_rows = {}, []
    for venue, values in tabs.items():
        if not values:
            continue
        tab_col = {name: i for i, name in enumerate(values[0])}
        for r in values[1:]:
            get = lambda name: r[tab_col[name]] if tab_col.get(name, len(r)) < len(r) else ""
            if not get("Title").strip():
                continue
            cells = {name: get(name) for name in header if name in tab_col}
            cells["Venue"] = cells.get("Venue") or venue
            k = _key(cells["Venue"], cells["Title"], cells.get("Start date", ""), cells.get("Times", ""))
            if k not in where:
                new_rows.append({**cells, "Status": cells.get("Status") or "Manual"})
                continue
            n = where[k]
            for name, value in cells.items():
                if value != rows[n][col[name]]:
                    edits[(n + 2, name)] = value
                    rows[n][col[name]] = value

    by_venue = {v: [] for v in venues}
    for r in rows:
        if r[col["Venue"]].strip():
            by_venue.setdefault(r[col["Venue"]].strip(), []).append(r)
    contents = {}
    for venue, vrows in by_venue.items():
        vrows.sort(key=lambda r: r[col["Start date"]], reverse=True)
        contents[venue] = [header] + vrows
    return edits, new_rows, contents


class VenueTabs:
    """One tab per venue holding that venue's rows from Screenings, newest first.

    The tabs are plain values (sortable, editable). Each refresh first carries any edits
    made on a venue tab back into Screenings, and adds rows typed there, then rewrites
    every venue tab from Screenings. Screenings stays the master list."""

    def __init__(self, tracker: TrackerSheet):
        self.tracker = tracker
        self.book = tracker.ws.spreadsheet

    def refresh(self) -> int:
        venue_names = [r[0] for r in self.book.worksheet("Venues").get_all_values()[1:] if r and r[0]]
        sheets = {ws.title: ws for ws in self.book.worksheets()}
        tab_names = [t for t in sheets if t not in CORE_TABS]
        current = {}
        if tab_names:
            got = self.book.values_batch_get([f"'{t}'" for t in tab_names])["valueRanges"]
            current = {t: vr.get("values", []) for t, vr in zip(tab_names, got)}

        edits, new_rows, contents = plan_venue_tabs(self.tracker.ws.get_all_values(), current, venue_names)
        if edits:
            header = self.tracker.ws.row_values(1)
            data = [{"range": f"'{TAB}'!{gspread.utils.rowcol_to_a1(n, header.index(name) + 1)}",
                     "values": [[_cell(name, value)]]} for (n, name), value in edits.items()]
            self.book.values_batch_update({"valueInputOption": "USER_ENTERED", "data": data})
        if new_rows:
            self.tracker.append_new(new_rows)
            # Re-read so the new rows land on their venue tabs too.
            _, _, contents = plan_venue_tabs(self.tracker.ws.get_all_values(), {}, venue_names)

        # Create missing tabs (after the core tabs, alphabetical), then rewrite them all.
        missing = sorted(v for v in contents if v not in sheets)
        if missing:
            self.book.batch_update({"requests": [
                {"addSheet": {"properties": {"title": v, "gridProperties": {"frozenRowCount": 1}}}}
                for v in missing]})
            sheets = {ws.title: ws for ws in self.book.worksheets()}
        self.book.values_batch_clear([f"'{v}'" for v in contents])
        header = contents[next(iter(contents))][0]
        self.book.values_batch_update({"valueInputOption": "USER_ENTERED", "data": [
            {"range": f"'{v}'!A1", "values": [header] + [[_cell(c, x) for c, x in zip(header, r)] for r in rows[1:]]}
            for v, rows in contents.items()]})

        requests = []
        for v, rows in contents.items():
            ws = sheets[v]
            need = max(len(rows) + 200, 500)
            if ws.row_count < need:
                requests.append({"appendDimension": {"sheetId": ws.id, "dimension": "ROWS", "length": need - ws.row_count}})
            requests.append({"setBasicFilter": {"filter": {"range": {
                "sheetId": ws.id, "startRowIndex": 0, "endRowIndex": max(ws.row_count, need),
                "startColumnIndex": 0, "endColumnIndex": len(header)}}}})
            requests.append({"repeatCell": {"range": {"sheetId": ws.id, "startRowIndex": 0, "endRowIndex": 1},
                                            "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                                            "fields": "userEnteredFormat.textFormat.bold"}})
        order = [TAB, MANUAL_TAB, "Films", "Venues"] + sorted(contents, key=str.lower)
        for i, name in enumerate(order):
            if name in sheets:
                requests.append({"updateSheetProperties": {"properties": {"sheetId": sheets[name].id, "index": i},
                                                           "fields": "index"}})
        self.book.batch_update({"requests": requests})
        return len(contents)
