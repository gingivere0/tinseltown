# TinselTown

Collects the coming week's screenings at Los Angeles movie theaters every Friday and adds them to the
[LA Theater Tracker](https://docs.google.com/spreadsheets/d/1XTy94LDxF2apCt8w-f6lAktS2zYt4ux-_JsuGuCO_HA/edit)
Google Sheet for review.

## How it works

1. `.github/workflows/weekly.yml` runs every Friday at 15:00 UTC, and on demand from the Actions tab.
2. Each venue in `venues.yaml` is opened in a headless browser, and its parser in `tinseltown/parsers`
   reads that week's screenings (title, dates, times, format, Q&As and other event notes), usually from
   the same data feed the site's own page uses. Everything runs on GitHub's free tier.
3. New screenings are appended to the sheet's Screenings tab with Status "Auto". Rows already in the
   sheet are left alone, so edits are never overwritten.
4. The week's results are also saved to `data/listings-<date>.csv`, and the run's summary page lists
   counts per venue, any venue that failed, and the venues to check by hand.

## Stats website

`site/` is a static page of charts and trivia about the tracker (busiest weeks, theaters, most-repeated
films, showtimes by hour and weekday, formats, events, decades, directors, series, and a film lookup).
`.github/workflows/site.yml` snapshots the sheet into `site/data/tinseltown.json` with the same service
account and publishes the folder to GitHub Pages every morning, after each listings run or Manual sync,
and whenever the site changes. It needs Pages turned on once: **Settings → Pages → Source: GitHub Actions**.
The Seen and Status columns stay out of the published data.

To work on the site locally, put a snapshot in place and serve the folder:

```
SHEET_ID=... GOOGLE_SERVICE_ACCOUNT_JSON="$(cat key.json)" python -m tinseltown export
python -m http.server -d site
```

## Setup

| Name | Kind | What it is |
| --- | --- | --- |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Actions secret | Key file of a Google Cloud service account; share the sheet with its email as an Editor |
| `SHEET_ID` | Actions variable | The ID from the sheet's URL |

## Running it

From the Actions tab, run **Weekly listings** with a start date, a comma-separated list of venues, or
"dry run" to collect without touching the sheet. Locally:

```
pip install -r requirements.txt && python -m playwright install chromium
python -m tinseltown run --dry-run --only "The New Beverly"
```

To add a theater, add an entry to `venues.yaml` and, if no existing parser fits, a parser module.
The **Snapshot venue pages** workflow saves what a site serves (HTML, text, and JSON requests) to the
`snapshots` branch, which is the easiest way to write or fix a parser.

Venues marked `manual` either turn away automated visitors (AMC, Lumiere, Brain Dead) or post
irregularly; the run summary links them for a quick check by hand.
