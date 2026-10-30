"""TCL Chinese Theatre: the Vista OCAPI film list and availability feeds the home page loads.

Formats are separate film records ("(IMAX) Resident Evil"), so they are folded into one row per film.
"""
import datetime as dt
import re

from .common import screening, week

PREFIX = re.compile(r"^\(([^)]+)\)\s*")
SKIP = {"Tour", "2D", "Subbed", "Early Access"}


def collect(fetcher, venue, start, end):
    page = fetcher.page(venue["urls"][0])
    films = {f["id"]: f for f in page.json("/ocapi/v1/films")["films"]}
    avail = page.json("/ocapi/v1/films/availability")
    attrs = {a["id"]: a["name"]["text"] for a in avail["relatedData"].get("attributes", [])}
    titles: dict[str, set] = {}
    for a in avail["filmAvailabilities"]:
        film = films.get(a["filmId"])
        if not film:
            continue
        release = dt.date.fromisoformat(film["releaseDate"][:10]) if film.get("releaseDate") else None
        playing = "NowShowing" in a["categories"] or (release and start <= release <= end)
        if not playing:
            continue
        raw = film["title"]["text"]
        tags = [attrs.get(i, "") for i in a["showtimeAttributeIds"]]
        if "Tour" in tags:
            continue
        m = PREFIX.match(raw)
        title = PREFIX.sub("", raw).strip()
        fmts = titles.setdefault(title, set())
        if m:
            fmts.add(m.group(1).replace(" Film", ""))
        fmts.update(t for t in tags if t and t not in SKIP and t != "Dolby Atmos")
    return [screening(venue, title, week(start, end), format_raw=", ".join(sorted(f)))
            for title, f in titles.items()]
