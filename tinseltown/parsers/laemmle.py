"""Laemmle Theatres: each theater page lists one day's films; ?date=YYYY-MM-DD picks the day."""
import datetime as dt

from bs4 import BeautifulSoup

from .common import screening, week


def collect(fetcher, venue, start, end):
    days: dict[str, set] = {}
    flags: dict[str, set] = {}
    for day in week(start, end):
        page = fetcher.page(f"{venue['urls'][0]}?date={day.isoformat()}", scroll=False)
        soup = BeautifulSoup(page.html, "html.parser")
        for movie in soup.select("div.movie"):
            link = movie.select_one(".title a")
            if not link or not movie.select(".showtime a"):
                continue
            title = link.get_text(" ", strip=True)
            days.setdefault(title, set()).add(day)
            for f in movie.select(".film-flags div"):
                label = f.get("data-original-title") or f.get_text(strip=True)
                if label and "Opens Today" not in label and "Caption" not in label and "subtitled" not in label:
                    flags.setdefault(title, set()).add(label)
    return [screening(venue, title, sorted(d), notes="; ".join(sorted(flags.get(title, ()))))
            for title, d in days.items()]
