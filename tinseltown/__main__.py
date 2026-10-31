"""python -m tinseltown run [--start YYYY-MM-DD] [--only VENUE ...] [--dry-run]
python -m tinseltown sync   (copy filled-in Manual rows into Screenings, then refresh the per-venue tabs)
python -m tinseltown export [--out PATH]   (snapshot the sheet for the stats website)"""
import argparse
import csv
import datetime as dt
import os
import pathlib
import sys
import traceback

import yaml

from .model import COLUMNS

ROOT = pathlib.Path(__file__).resolve().parent.parent


def next_friday(today: dt.date) -> dt.date:
    return today + dt.timedelta(days=(4 - today.weekday()) % 7)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="tinseltown")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="collect a week of listings")
    run.add_argument("--start", type=dt.date.fromisoformat, help="first day of the week (default: this Friday)")
    run.add_argument("--only", nargs="*", default=[], help="venue names to limit the run to")
    run.add_argument("--dry-run", action="store_true", help="write the CSV but not the sheet")
    sub.add_parser("sync", help="copy filled-in Manual rows into Screenings and refresh the venue tabs")
    export = sub.add_parser("export", help="snapshot the sheet for the stats website")
    export.add_argument("--out", type=pathlib.Path, default=ROOT / "site" / "data" / "tinseltown.json")
    args = parser.parse_args(argv)

    if args.cmd == "export":
        from .export import export as export_sheet
        n = export_sheet(os.environ["SHEET_ID"], os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"], args.out)
        print(f"{n} screenings written to {args.out}")
        return 0

    if args.cmd == "sync":
        from .sheet import ManualSheet, TrackerSheet, VenueTabs
        tracker = TrackerSheet(os.environ["SHEET_ID"], os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
        print(f"{ManualSheet(tracker).sync()} manual rows copied into Screenings")
        print(f"{VenueTabs(tracker).refresh()} venue tabs refreshed")
        return 0

    from .fetch import PageFetcher
    from .model import merge
    from .parsers import PARSERS

    start = args.start or next_friday(dt.date.today())
    venues = yaml.safe_load((ROOT / "venues.yaml").read_text())
    if args.only:
        wanted = {v.lower() for v in args.only}
        venues = [v for v in venues if v["venue"].lower() in wanted]

    end = start + dt.timedelta(days=6)
    rows, report, manual = [], [], []
    with PageFetcher() as fetcher:
        for venue in venues:
            if venue.get("manual"):
                manual.append(venue)
                continue
            try:
                found = merge(PARSERS[venue["parser"]](fetcher, venue, start, end))
                rows += [s.row(weekly=venue.get("style") == "weekly") for s in found]
                report.append((venue["venue"], len(found), ""))
            except Exception as exc:  # one broken site should not stop the rest
                traceback.print_exc()
                report.append((venue["venue"], 0, f"{type(exc).__name__}: {exc}"[:200]))
            print(f"{report[-1][0]}: {report[-1][1]} {report[-1][2]}", flush=True)

    out = ROOT / "data" / f"listings-{start.isoformat()}.csv"
    out.parent.mkdir(exist_ok=True)
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    added = None
    if not args.dry_run and os.environ.get("SHEET_ID") and os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"):
        from .sheet import ManualSheet, TrackerSheet, VenueTabs
        tracker = TrackerSheet(os.environ["SHEET_ID"], os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
        added = tracker.append_new(rows)
        # Venues to fill in by hand this week: the ones we never read, plus any whose site broke.
        by_name = {v["venue"]: v for v in venues}
        todo = [(v["venue"], v["urls"][0], v.get("why", "Site can't be read automatically")) for v in manual]
        todo += [(name, by_name[name]["urls"][0], f"Automatic collection failed this week ({err.split(':')[0]})")
                 for name, _, err in report if err]
        manual_tab = ManualSheet(tracker)
        manual_tab.add_week(start.isoformat(), todo)
        manual_tab.sync()
        VenueTabs(tracker).refresh()

    summary = [f"## Listings for the week of {start:%B %-d, %Y}", ""]
    summary.append(f"{len(rows)} screenings collected" +
                   (f", {added} new rows added to the sheet." if added is not None else ", sheet not updated."))
    summary += ["", "| Venue | Screenings | Problem |", "| --- | --- | --- |"]
    summary += [f"| {v} | {n} | {err} |" for v, n, err in report]
    if manual:
        summary += ["", "Check by hand:"] + [f"- [{v['venue']}]({v['urls'][0]})" for v in manual]
    text = "\n".join(summary)
    print(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
