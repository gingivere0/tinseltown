"""Append new screenings to the Screenings tab of the tracker sheet."""
import json

import gspread
from google.oauth2.service_account import Credentials


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
