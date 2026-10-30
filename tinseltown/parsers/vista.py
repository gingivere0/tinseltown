"""Vista Theater: the now-playing page, where each film's dates and times come just before its title."""
import datetime as dt
import re

from .common import screening, title_case

MONTHS = ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY", "AUGUST",
          "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"]
DAY = re.compile(r"^(\d{1,2})(ST|ND|RD|TH)$")
TIME = re.compile(r"^\d{1,2}:\d{2} [AP]M$")
INFO = re.compile(r"^(\d{4}) \| [^|]+ \| (.+)$")


def collect(fetcher, venue, start, end):
    lines = [l.strip() for l in fetcher.page(venue["urls"][0]).text.splitlines() if l.strip()]
    out, slots, tags = [], [], []
    month = day = None
    for i, line in enumerate(lines):
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if line in MONTHS:
            month = MONTHS.index(line) + 1
        elif (m := DAY.match(line)) and month:
            day = int(m.group(1))
        elif TIME.match(line) and month and day:
            year = start.year if month >= start.month - 1 else start.year + 1
            slots.append((dt.date(year, month, day), line.lower()))
        elif (info := INFO.match(nxt)) and slots:
            title = re.sub(r"\s+[–-]\s+EARLY ACCESS PREVIEW$", "", line)
            notes = tags + (["Early access preview"] if title != line else [])
            by_time: dict[str, list] = {}
            for d, t in slots:
                if start <= d <= end:
                    by_time.setdefault(t, []).append(d)
            for t, dates in by_time.items():
                out.append(screening(venue, title_case(title), dates, times=t, year=info.group(1),
                                     format_raw=info.group(2), notes="; ".join(n.title() for n in notes)))
            slots, tags, month, day = [], [], None, None
        elif slots and line.isupper() and len(line) < 30 and not INFO.match(line):
            tags.append(line)  # labels such as MATINEE between the dates and the title
    return out
