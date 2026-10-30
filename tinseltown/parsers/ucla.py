"""UCLA Film & Television Archive (Billy Wilder Theater): the search feed the events page loads."""
import datetime as dt
import json

from .common import clean, screening, time_label


def collect(fetcher, venue, start, end):
    page = fetcher.page(venue["urls"][0])
    hits = {}
    for url, body in page.responses:
        if "_search" in url:
            for h in json.loads(body).get("hits", {}).get("hits", []):
                if h["_source"].get("startDateWithTime"):  # some queries return partial records
                    hits[h["_id"]] = h["_source"]
    out = []
    for s in hits.values():
        if not s.get("startDateWithTime"):
            continue
        when = dt.datetime.fromisoformat(s["startDateWithTime"])
        if not start <= when.date() <= end:
            continue
        details = s.get("ftvaEventScreeningDetails") or []
        first = details[0] if details else {}
        year = (first.get("year") or "")[-4:]
        tags = [t["title"] for d in details for t in d.get("tagLabels", [])]
        notes = clean(s.get("guestSpeaker") or "")
        out.append(screening(
            venue, clean(s["title"]), [when.date()], times=time_label(when),
            year=year if len(details) == 1 else "", format_raw=", ".join(dict.fromkeys(tags)),
            notes=notes, series=clean(s.get("eventSeriesTitle") or ""),
            source=f"https://www.cinema.ucla.edu/{s.get('uri', '')}"))
    return out
