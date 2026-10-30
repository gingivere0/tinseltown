"""Append new screenings to the Screenings tab of the tracker sheet."""
import json

import gspread
from google.oauth2.service_account import Credentials


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
TAB = "Screenings"


def _key(venue: str, title: str, start: str, times: str) -> tuple:
    return (venue.lower().strip(), title.lower().strip(), start.strip(), times.lower().strip())


def _safe(value: str) -> str:
    # Keep titles like "=Equals" or "+1" from being read as formulas.
    return "'" + value if value[:1] in ("=", "+", "-", "@") else value


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
            new.append([_safe(str(row.get(col, ""))) for col in header])
        if new:
            self.ws.append_rows(new, value_input_option="USER_ENTERED", table_range="A1")
        return len(new)
