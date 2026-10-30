# TinselTown

Collects the coming week's screenings at Los Angeles movie theaters every Friday and adds them to the
[LA Theater Tracker](https://docs.google.com/spreadsheets/d/1XTy94LDxF2apCt8w-f6lAktS2zYt4ux-_JsuGuCO_HA/edit)
Google Sheet for review.

## How it works

1. `.github/workflows/weekly.yml` runs every Friday at 15:00 UTC, and on demand from the Actions tab.
2. Each venue in `venues.yaml` is opened in a headless browser, and Claude pulls that week's screenings
   (title, dates, times, format, Q&As and other event notes) out of the page text.
3. New screenings are appended to the sheet's Screenings tab with Status "Auto". Rows already in the
   sheet are left alone, so edits are never overwritten.
4. The week's results are also saved to `data/listings-<date>.csv`, and the run's summary page lists
   counts per venue, any venue that failed, and the venues to check by hand.

## Setup

| Name | Kind | What it is |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | Actions secret | Claude API key used for extraction |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Actions secret | Key file of a Google Cloud service account; share the sheet with its email as an Editor |
| `SHEET_ID` | Actions variable | The ID from the sheet's URL |

## Running it

From the Actions tab, run **Weekly listings** with a start date, a comma-separated list of venues, or
"dry run" to collect without touching the sheet. Locally:

```
pip install -r requirements.txt && python -m playwright install chromium
python -m tinseltown run --dry-run --only "The New Beverly"
```

To add a theater, add an entry to `venues.yaml`.
