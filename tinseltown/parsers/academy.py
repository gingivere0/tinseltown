"""Academy Museum: the ticketing feed the calendar page loads."""
import datetime as dt
from zoneinfo import ZoneInfo

from .common import clean, screening, time_label

LA = ZoneInfo("America/Los_Angeles")


def collect(fetcher, venue, start, end):
    page = fetcher.page(venue["urls"][0])
    data = page.json("tickets.academymuseum.org/cached_api/events/available?")
    templates = {t["id"]: t for t in data["event_template"]["_data"]}
    rooms = {v["id"]: v["name"] for v in data["venue"]["_data"]}
    out = []
    for s in data["event_session"]["_data"]:
        t = templates.get(s["event_template_id"])
        if not t or not t.get("category", "").startswith("Film Screening"):
            continue
        when = dt.datetime.fromisoformat(s["start_datetime"].replace("Z", "+00:00")).astimezone(LA)
        if not start <= when.date() <= end:
            continue
        notes = []
        if ":" in t["category"]:
            notes.append(t["category"].split(":", 1)[1].strip())  # Matinee, Double Feature
        if t.get("subtitle"):
            notes.append(clean(t["subtitle"]))
        if s.get("sold_out"):
            notes.append("Sold out")
        description = clean(t.get("summary") or "") + " " + clean(t.get("description") or "")
        out.append(screening(
            venue, clean(t["name"]), [when.date()], times=time_label(when),
            screen=rooms.get(t.get("venue_id"), ""), notes="; ".join(n for n in notes if n),
            extra_formats=[f for f in ("35mm", "70mm", "16mm", "Nitrate") if f.lower() in description.lower()]))
    return out
