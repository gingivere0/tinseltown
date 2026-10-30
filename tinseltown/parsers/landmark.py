"""Landmark Theatres: the per-theater schedule (movie id -> days) and movie details the theater page loads."""
import datetime as dt
import json

from .common import screening

API = "https://www.landmarktheatres.com/api/gatsby-source-boxofficeapi"


def collect(fetcher, venue, start, end):
    page = fetcher.page(venue["urls"][0])
    sched = page.json(f"scheduledMovies?theaterId={venue['theater_id']}")
    movies = {}
    for url, body in page.responses:
        if "gatsby-source-boxofficeapi/movies?" in url:
            for m in json.loads(body):
                movies[m["id"]] = m
    playing = {}
    for movie_id, days in sched.get("scheduledDays", {}).items():
        dates = [d for d in (dt.date.fromisoformat(x) for x in days) if start <= d <= end]
        if dates:
            playing[movie_id] = dates
    missing = [i for i in playing if i not in movies]
    if missing:  # the page only loads details for the films it shows first
        query = "&".join(f"ids={i}" for i in missing)
        try:
            for m in fetcher.get_json(f"{API}/movies?basic=false&castingLimit=3&{query}"):
                movies[m["id"]] = m
        except (LookupError, RuntimeError):
            pass
    out = []
    for movie_id, dates in playing.items():
        m = movies.get(movie_id, {})
        directors = ", ".join(
            f"{n['person'].get('firstName', '')} {n['person'].get('lastName', '')}".strip()
            for n in (m.get("directors") or {}).get("nodes", []))
        release = sched.get("releaseDates", {}).get(movie_id, "")
        out.append(screening(venue, m.get("title", f"Movie {movie_id}"), dates,
                             year=release[:4], director=directors))
    return out
