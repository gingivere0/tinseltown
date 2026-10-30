"""Turn a venue page's text into screenings with Claude."""
import datetime as dt
import json
import os

import anthropic

from .model import Screening
from . import normalize

MODEL = os.environ.get("TINSELTOWN_MODEL", "claude-opus-5-5")

SCHEMA = {
    "type": "object",
    "properties": {
        "screenings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "dates": {"type": "array", "items": {"type": "string"},
                              "description": "Each date it plays, YYYY-MM-DD"},
                    "times": {"type": "string",
                              "description": "Showtimes as listed, e.g. '7:30 pm' or '2:00 pm, 7:30 pm'; empty if none shown"},
                    "screen": {"type": "string", "description": "Room or sub-venue if the page names one"},
                    "format": {"type": "string", "description": "Projection or premium formats as listed, e.g. '35mm', 'IMAX, Dolby'"},
                    "year": {"type": "string", "description": "Release year only if the page states it"},
                    "director": {"type": "string", "description": "Director only if the page states it"},
                    "series": {"type": "string", "description": "Programming series or festival name, if any"},
                    "notes": {"type": "string",
                              "description": "Special-event details: Q&A or intro guests, double-feature partner ('DF w/ ...'), premieres, restorations, print notes, sold out"},
                },
                "required": ["title", "dates", "times", "screen", "format", "year", "director", "series", "notes"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["screenings"],
    "additionalProperties": False,
}

STYLE_HINTS = {
    "repertory": "List each film once per distinct showtime pattern, with every date it plays in the window.",
    "weekly": ("This is a first-run multiplex. List each film playing during the window once, with its "
               "dates in the window; leave times empty. Put premium formats (IMAX, Dolby, 70mm, RealD 3D, "
               "ScreenX, PRIME, XL, D-BOX) in format, and fan events or Q&As in notes."),
}


class Extractor:
    def __init__(self):
        self.client = anthropic.Anthropic()

    def screenings(self, venue: dict, page_text: str, start: dt.date, days: int = 7) -> list[Screening]:
        end = start + dt.timedelta(days=days - 1)
        instructions = (
            f"Below is the text of the listings page for {venue['venue']}, a movie theater in Los Angeles. "
            f"Extract every film screening from {start:%A %B %d, %Y} through {end:%A %B %d, %Y}. "
            f"{STYLE_HINTS[venue.get('style', 'repertory')]} "
            f"{venue.get('filter', '')} "
            "Use the film's title as the theater lists it, without the venue name or format suffixes. "
            "Skip non-film events (concerts, parties, classes) unless a film is shown. "
            "If the page has nothing in the window, return an empty list."
        )
        response = self.client.beta.messages.create(
            model=MODEL,
            max_tokens=32000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
            messages=[{"role": "user", "content": f"{instructions}\n\n<page>\n{page_text}\n</page>"}],
        )
        if response.stop_reason == "refusal":
            raise RuntimeError(f"model declined the page for {venue['venue']}")
        if response.stop_reason == "max_tokens":
            raise RuntimeError(f"extraction for {venue['venue']} ran past max_tokens")
        text = next(b.text for b in response.content if b.type == "text")
        items = json.loads(text)["screenings"]

        out = []
        for item in items:
            dates = []
            for d in item["dates"]:
                try:
                    day = dt.date.fromisoformat(d)
                except ValueError:
                    continue
                if start <= day <= end:
                    dates.append(day)
            if not dates or not item["title"].strip():
                continue
            out.append(Screening(
                venue=venue["venue"], chain=venue.get("chain", venue["venue"]),
                title=item["title"].strip(), dates=dates, screen=item["screen"].strip(),
                times=item["times"].strip(), year=item["year"].strip(),
                director=item["director"].strip(), formats=normalize.formats(item["format"]),
                format_raw=item["format"].strip(),
                events=normalize.events(item["notes"], item["title"]),
                series=item["series"].strip(), notes=item["notes"].strip(),
                source=venue["urls"][0],
            ))
        return out
