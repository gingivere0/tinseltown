from dataclasses import dataclass, field, asdict
import datetime as dt

# Column order of the Screenings tab. The sheet writer and the CSV archive both use it.
COLUMNS = [
    "Venue", "Chain or group", "Screen", "Title", "Year", "Director",
    "Start date", "End date", "Dates (as listed)", "Times", "Format",
    "Events", "Series", "Notes", "Seen", "Status", "Format (as listed)", "Source file",
]

DAY_NAMES = ["Mon", "Tues", "Wed", "Thurs", "Fri", "Sat", "Sun"]


@dataclass
class Screening:
    venue: str
    chain: str
    title: str
    dates: list[dt.date]
    screen: str = ""
    times: str = ""
    year: str = ""
    director: str = ""
    formats: list[str] = field(default_factory=list)
    format_raw: str = ""
    events: list[str] = field(default_factory=list)
    series: str = ""
    notes: str = ""
    source: str = ""

    def key(self) -> tuple:
        """Identity used to avoid adding the same screening twice."""
        start = min(self.dates).isoformat() if self.dates else ""
        return (self.venue.lower(), self.title.lower().strip(), start, self.times.lower().strip())

    def row(self, weekly: bool = False) -> dict:
        start = min(self.dates) if self.dates else None
        end = max(self.dates) if self.dates else None
        return {
            "Venue": self.venue,
            "Chain or group": self.chain,
            "Screen": self.screen,
            "Title": self.title,
            "Year": self.year,
            "Director": self.director,
            "Start date": start.isoformat() if start else "",
            "End date": end.isoformat() if end else "",
            "Dates (as listed)": format_dates(self.dates, weekly),
            "Times": self.times,
            "Format": "; ".join(self.formats),
            "Events": "; ".join(self.events),
            "Series": self.series,
            "Notes": self.notes,
            "Seen": "",
            "Status": "Auto",
            "Format (as listed)": self.format_raw,
            "Source file": self.source,
        }


def format_dates(dates: list[dt.date], weekly: bool = False) -> str:
    """Render dates the way Jonathan writes them: '01.13 Tues - 01.15 Thurs',
    '01.02 Fri, 01.09 Fri', or '01.02 - 01.09' for a chain's weekly block."""
    if not dates:
        return ""
    ds = sorted(set(dates))
    md = lambda d: d.strftime("%m.%d")
    label = lambda d: f"{md(d)} {DAY_NAMES[d.weekday()]}"
    if weekly:
        return f"{md(ds[0])} - {md(ds[0] + dt.timedelta(days=7))}"
    if len(ds) == 1:
        return label(ds[0])
    consecutive = all((b - a).days == 1 for a, b in zip(ds, ds[1:]))
    if consecutive:
        return f"{label(ds[0])} - {label(ds[-1])}"
    return ", ".join(label(d) for d in ds)


def merge(screenings: list[Screening]) -> list[Screening]:
    """Combine single-day entries for the same film, showtime, and notes into one run."""
    groups: dict[tuple, Screening] = {}
    for s in screenings:
        k = (s.venue, s.screen, s.title.lower(), s.times.lower(), s.notes)
        if k in groups:
            groups[k].dates = sorted(set(groups[k].dates + s.dates))
            for f in s.formats:
                if f not in groups[k].formats:
                    groups[k].formats.append(f)
        else:
            groups[k] = s
    return sorted(groups.values(), key=lambda s: (min(s.dates), s.title))
