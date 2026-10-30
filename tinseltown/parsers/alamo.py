"""Alamo Drafthouse Los Angeles: the market schedule feed drafthouse.com loads."""
import datetime as dt

from .common import clean, screening


def collect(fetcher, venue, start, end):
    page = fetcher.page(venue["urls"][0])
    data = page.json("/schedule/market/los-angeles")["data"]
    formats = {f["slug"]: f["title"] for f in data.get("formats", [])}
    presentations = {p["slug"]: p for p in data["presentations"]}
    by_show: dict[str, dict] = {}
    for s in data["sessions"]:
        if s.get("isHidden") or s.get("status") == "CANCELLED":
            continue
        day = dt.date.fromisoformat(s["businessDateClt"])
        if not start <= day <= end:
            continue
        entry = by_show.setdefault(s["presentationSlug"], {"dates": set(), "formats": set()})
        entry["dates"].add(day)
        if s.get("formatSlug"):
            entry["formats"].add(formats.get(s["formatSlug"], s["formatSlug"]))
    out = []
    for slug, entry in by_show.items():
        p = presentations.get(slug, {})
        show = p.get("show") or {}
        title = show.get("title") or slug.replace("-", " ").title()
        notes, series = [], ""
        if p.get("superTitle"):
            series = p["superTitle"].get("superTitle", "")
        event = p.get("event") or {}
        if event.get("eventTypeTitleOverride"):
            notes.append(event["eventTypeTitleOverride"])
        if event.get("headline"):
            notes.append(clean(event["headline"]))
        fmt = ", ".join(sorted(f for f in entry["formats"] if f != "2D Digital"))
        out.append(screening(venue, title, sorted(entry["dates"]), format_raw=fmt,
                             notes="; ".join(notes), series=series,
                             source=f"https://drafthouse.com/los-angeles/show/{show.get('slug', slug)}"))
    return out
