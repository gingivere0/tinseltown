"""Snapshot the tracker sheet into the JSON file the stats website reads."""
import datetime as dt
import json

# Screenings columns the website uses (Seen and Status stay private to the sheet).
SITE_COLUMNS = [
    "Venue", "Chain or group", "Screen", "Title", "Year", "Director", "Start date", "End date",
    "Dates (as listed)", "Times", "Format", "Events", "Series", "Notes", "Link",
]
FILM_FIELDS = {"Year": "year", "Director": "director", "Runtime (min)": "runtime", "Country": "country"}
DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%Y/%m/%d")


def _date(value: str) -> str:
    value = value.strip()
    for fmt in DATE_FORMATS:
        try:
            return dt.datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    return ""


def _records(values: list[list[str]]) -> list[dict]:
    if not values:
        return []
    header = values[0]
    return [{h: (r[i].strip() if i < len(r) else "") for i, h in enumerate(header)} for r in values[1:]]


def build(screenings: list[list[str]], films: list[list[str]], venues: list[list[str]], updated: str) -> dict:
    """Turn raw tab values (as get_all_values returns them) into the site's data file."""
    film_info = {}
    for f in _records(films):
        info = {key: f.get(col, "") for col, key in FILM_FIELDS.items() if f.get(col, "")}
        if f.get("Title") and info:
            film_info[f["Title"].lower()] = info

    rows = []
    for s in _records(screenings):
        if not s.get("Title") or not s.get("Venue"):
            continue
        start = _date(s.get("Start date", ""))
        if not start:
            continue
        info = film_info.get(s["Title"].lower(), {})
        s["Start date"] = start
        s["End date"] = _date(s.get("End date", "")) or start
        s["Year"] = s.get("Year") or info.get("year", "")
        s["Director"] = s.get("Director") or info.get("director", "")
        source = s.get("Source file", "")
        s["Link"] = source if source.startswith("http") else ""
        rows.append([s.get(c, "") for c in SITE_COLUMNS])

    return {
        "updated": updated,
        "columns": SITE_COLUMNS,
        "rows": rows,
        "films": {title: info for title, info in film_info.items()},
        "venues": [{"venue": v.get("Venue", ""), "chain": v.get("Chain or group", ""), "status": v.get("Status", "")}
                   for v in _records(venues) if v.get("Venue")],
    }


def export(sheet_id: str, service_account_json: str, out) -> int:
    import gspread
    from google.oauth2.service_account import Credentials

    creds = Credentials.from_service_account_info(
        json.loads(service_account_json), scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
    book = gspread.authorize(creds).open_by_key(sheet_id)
    tab = lambda name: book.worksheet(name).get_all_values()
    updated = dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes")
    data = build(tab("Screenings"), tab("Films"), tab("Venues"), updated)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    return len(data["rows"])
