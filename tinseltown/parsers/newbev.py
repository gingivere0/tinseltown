"""New Beverly Cinema: thenewbev.com/schedule, one card per show (double features share a card)."""
import datetime as dt
import re

from bs4 import BeautifulSoup

from .common import clean, screening, split_year, title_case

MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"], start=1)}
TAG = re.compile(r"\s*\(([^)]*)\)\s*$")


def collect(fetcher, venue, start, end):
    page = fetcher.page(venue["urls"][0])
    soup = BeautifulSoup(page.html, "html.parser")
    out = []
    for card in soup.select("article.event-card"):
        month = MONTHS[card.select_one(".event-card__month").get_text(strip=True).lower()]
        day = int(card.select_one(".event-card__numb").get_text(strip=True))
        year = start.year if month >= start.month - 1 else start.year + 1
        date = dt.date(year, month, day)
        if not start <= date <= end:
            continue
        times = [t.get_text(strip=True) for t in card.select("time.event-card__time")]
        raw = card.select_one(".event-card__title").decode_contents()
        titles = [clean(t) for t in re.split(r"/\s*<br\s*/?>", raw) if clean(t)]
        link = card.select_one("a")["href"] if card.select_one("a") else ""
        for i, full in enumerate(titles):
            title, notes = full, []
            # Trailing tags such as "(IB TECH PRINT)" or "(SCHEDULE CHANGE)"; a year stays in the title.
            while (m := TAG.search(title)) and not re.fullmatch(r"\d{4}", m.group(1)):
                notes.insert(0, m.group(1).title())
                title = title[:m.start()]
            title, year_ = split_year(title)
            partner = [t for j, t in enumerate(titles) if j != i]
            if partner:
                notes.append("DF w/ " + title_case(split_year(TAG.sub("", partner[0]))[0]))
            note = "; ".join(notes)
            out.append(screening(
                venue, title_case(title), [date], times=times[i] if i < len(times) else ", ".join(times),
                year=year_, format_raw="35mm IB Tech" if "ib tech" in note.lower() else "",
                notes=note, source=link))
    return out
