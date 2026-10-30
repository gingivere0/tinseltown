"""Vidiots: each day's page (vidiotsfoundation.org/YYYY-MM-DD) carries schema.org ScreeningEvent data."""
import datetime as dt
import json
import re

from .common import screening, time_label, week

LD = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)


def collect(fetcher, venue, start, end):
    base = venue["urls"][0].rstrip("/")
    found = []
    for day in week(start, end):
        page = fetcher.page(f"{base}/{day.isoformat()}", scroll=False)
        graph = []
        for block in LD.findall(page.html):
            data = json.loads(block)
            graph += data.get("@graph", [data])
        films = {g["@id"]: g for g in graph if g.get("@type") == "Movie" and "@id" in g}
        for g in graph:
            if g.get("@type") != "ScreeningEvent":
                continue
            when = dt.datetime.fromisoformat(g["startDate"])
            if when.date() != day:
                continue
            film = films.get((g.get("workPresented") or {}).get("@id"), {})
            title = film.get("name") or g["name"].split(" - ")[0]
            directors = ", ".join(p["name"] for p in film.get("director", []))
            sold_out = all("SoldOut" in o.get("availability", "") for o in g.get("offers", [])) and g.get("offers")
            found.append(screening(venue, title, [day], times=time_label(when),
                                   year=(film.get("dateCreated") or "")[:4], director=directors,
                                   notes="Sold out" if sold_out else "", source=film.get("url", "")))
    return found
