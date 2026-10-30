import datetime as dt
import html
import re

from bs4 import BeautifulSoup

from ..model import Screening
from .. import normalize


def clean(text: str) -> str:
    """Strip tags and entities and collapse whitespace."""
    text = BeautifulSoup(html.unescape(text or ""), "html.parser").get_text(" ")
    return re.sub(r"\s+", " ", text).strip()


def time_label(t: dt.datetime | dt.time) -> str:
    """'7:30 pm', the way Jonathan writes times."""
    return t.strftime("%I:%M %p").lstrip("0").lower()


def title_case(title: str) -> str:
    """Sites that shout titles in capitals get title case; mixed case is left alone."""
    if title.upper() != title:
        return title
    small = {"a", "an", "and", "as", "at", "but", "by", "for", "in", "of", "on", "or", "the", "to", "vs", "with"}
    words = title.lower().split(" ")
    out = []
    for i, w in enumerate(words):
        if i and w in small:
            out.append(w)
        else:
            out.append(re.sub(r"^([^a-z]*)([a-z])", lambda m: m.group(1) + m.group(2).upper(), w))
    return " ".join(out)


YEAR = re.compile(r"\s*\((\d{4})\)\s*$")


def split_year(title: str) -> tuple[str, str]:
    """'The Fly (1986)' -> ('The Fly', '1986')."""
    m = YEAR.search(title)
    return (title[:m.start()].strip(), m.group(1)) if m else (title.strip(), "")


def screening(venue: dict, title: str, dates, *, times="", screen="", year="", director="",
              format_raw="", notes="", series="", source="", extra_formats=()) -> Screening:
    formats = normalize.formats(format_raw)
    for f in list(extra_formats) + normalize.formats_in_text(notes):
        if f not in formats:
            formats.append(f)
    return Screening(
        venue=venue["venue"], chain=venue.get("chain", venue["venue"]), title=title,
        dates=list(dates), screen=screen, times=times, year=year, director=director,
        formats=formats, format_raw=format_raw, events=normalize.events(notes, title),
        series=series, notes=notes, source=source or venue["urls"][0],
    )


def week(start: dt.date, end: dt.date) -> list[dt.date]:
    return [start + dt.timedelta(days=i) for i in range((end - start).days + 1)]
