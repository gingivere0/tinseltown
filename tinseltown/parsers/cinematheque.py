"""American Cinematheque (Aero, Egyptian, Los Feliz 3, Directors Village, Culver): the events
feed the now-showing page loads from the site's WordPress API."""
import datetime as dt
import re

from .common import clean, screening, title_case

PAGE = "https://www.americancinematheque.com/now-showing/?view_type=list"
# Series names are quoted: 'Bleak Week: Cinema of Despair' and 'Starring Catherine O'Hara'.
SERIES = re.compile(r"[‘'“]([^‘’“”]{4,}?)['’”](?=\s*(?:and\b|\||$|[A-Z]))")


def _same_place(text: str, venue: dict) -> bool:
    norm = lambda s: re.sub(r"^the\s+|\s+(theatre|theater)$", "", s.lower().strip())
    return bool(text) and norm(text) in {norm(venue["venue"]), norm(venue["location"])}


def _taxonomy(page) -> dict[str, dict[int, str]]:
    tax = page.json("/wp-json/wp/v2/event/taxonomies")["taxonomies"]
    return {name: {t["term_id"]: t["name"] for t in tax[name]["list"]}
            for name in ("event_location", "event_format", "event_type")}


def collect(fetcher, venue, start, end):
    page = fetcher.page(PAGE)
    names = _taxonomy(page)
    hits = page.json("algolia_get_events")["hits"]
    out = []
    for h in hits:
        locations = {names["event_location"].get(i, "") for i in h.get("event_location", [])}
        if venue["location"] not in locations:
            continue
        date = dt.datetime.strptime(h["event_start_date"], "%Y%m%d").date()
        if not start <= date <= end:
            continue
        types = [names["event_type"].get(i, "") for i in h.get("event_type", [])]
        if not {"Film", "Double Feature", "Triple Feature", "Shorts Program", "Television",
                "Marathon", "Advance Screening", "Premiere", "Single Feature"} & set(types):
            continue  # panels, mixers, book signings
        fmt = ", ".join(names["event_format"].get(i, "") for i in h.get("event_format", []))
        # The card excerpt reads "Los Feliz 3 | Q&A with ... | 'Series Name'".
        excerpt = clean(h.get("event_card_excerpt", ""))
        parts = [p.strip() for p in excerpt.split("|")]
        screen, details = (parts[0], " | ".join(parts[1:])) if len(parts) > 1 else ("", excerpt)
        if _same_place(details, venue) and len(parts) == 1:
            details = ""
        if _same_place(screen, venue):
            screen = ""
        series = "; ".join(m.strip() for m in SERIES.findall(details))
        title = clean(h["title"])
        out.append(screening(
            venue, title_case(title), [date], times=h.get("event_start_time", "").lower(),
            screen=screen,
            format_raw=fmt, notes=details, series=series, source=h.get("url", ""),
            extra_formats=["Nitrate"] if "Nitrate" in fmt else []))
    return out
