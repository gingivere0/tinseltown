"""El Capitan Theatre: the run cards on the home page ("OCT 30 - NOV 01")."""
import datetime as dt
import re

from .common import screening

RANGE = re.compile(r"^([A-Z]{3}) (\d{1,2})(?: - ([A-Z]{3}) (\d{1,2}))?$")
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


def _date(mon: str, day: str, start: dt.date) -> dt.date:
    m = MONTHS.index(mon) + 1
    year = start.year if m >= start.month - 1 else start.year + 1
    return dt.date(year, m, int(day))


def collect(fetcher, venue, start, end):
    lines = [l.strip() for l in fetcher.page(venue["urls"][0]).text.splitlines() if l.strip()]
    seen, out = set(), []
    for i, line in enumerate(lines[1:], start=1):
        m = RANGE.match(line)
        if not m:
            continue
        title = lines[i - 1]
        first = _date(m.group(1), m.group(2), start)
        last = _date(m.group(3), m.group(4), start) if m.group(3) else first
        if (title, first) in seen or last < start or first > end:
            continue
        seen.add((title, first))
        days = [first + dt.timedelta(days=d) for d in range((last - first).days + 1)]
        days = [d for d in days if start <= d <= end]
        fmt = "4D" if re.search(r"\b4D\b", title) else ""
        out.append(screening(venue, re.sub(r"\s+in 4D$", "", title), days, format_raw=fmt,
                             notes="Fan event" if "Fan Event" in title else ""))
    return out
