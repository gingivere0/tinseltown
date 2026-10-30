"""Acropolis Cinema: the screening calendar on the home page (date, time, title, director line, note)."""
import datetime as dt
import re

from .common import screening

DATE = re.compile(r"^[A-Z][a-z]+ \d{1,2}, \d{4}$")
TIME = re.compile(r"^\d{1,2}:\d{2}\s*[ap]m$", re.I)
DIRECTOR = re.compile(r"^\(Dir\.\s*(.+?)\)$")


def collect(fetcher, venue, start, end):
    text = fetcher.page(venue["urls"][0]).text
    text = text.split("SCREENING CALENDAR", 1)[-1].split("PAST SCREENINGS", 1)[0]
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    out = []
    for i, line in enumerate(lines):
        if not (DATE.match(line) and i + 2 < len(lines) and TIME.match(lines[i + 1])):
            continue
        day = dt.datetime.strptime(line, "%B %d, %Y").date()
        if not start <= day <= end:
            continue
        title = lines[i + 2]
        director = year = note = ""
        rest = lines[i + 3:i + 6]
        if rest and (m := DIRECTOR.match(rest[0])):
            credits = m.group(1)
            if ";" not in credits:  # one film: "Kaori Oda, 2019"
                director, _, year = credits.rpartition(", ")
            else:
                note = f"Dir. {credits}"
            rest = rest[1:]
        if rest and rest[0] not in ("MORE INFO", "BUY TICKETS"):
            note = "; ".join(n for n in (note, rest[0]) if n)
        out.append(screening(venue, title, [day], times=lines[i + 1].lower(),
                             director=director, year=year, notes=note))
    return out
