"""Los Angeles Filmforum: the schedule page, one block per program ("Date: Jul 5, 2026 1:00PM")."""
import datetime as dt
import re

from .common import screening, time_label

DATE = re.compile(r"^Date:\s*(\w{3} \d{1,2}, \d{4})\s+(\d{1,2}:\d{2}\s*[AP]M)", re.I)


def collect(fetcher, venue, start, end):
    lines = [l.strip() for l in fetcher.page(venue["urls"][0]).text.splitlines() if l.strip()]
    out = []
    for i, line in enumerate(lines):
        m = DATE.match(line)
        if not m:
            continue
        when = dt.datetime.strptime(f"{m.group(1)} {m.group(2).replace(' ', '')}", "%b %d, %Y %I:%M%p")
        if not start <= when.date() <= end:
            continue
        title = lines[i - 1]
        location = lines[i + 1].removeprefix("Location:").strip() if i + 1 < len(lines) else ""
        blurb = lines[i + 2] if i + 2 < len(lines) and lines[i + 2] != "Details" else ""
        out.append(screening(venue, title, [when.date()], times=time_label(when),
                             screen=location, notes=blurb[:300]))
    return out
