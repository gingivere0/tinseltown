"""Stand-in for PageFetcher that serves pages from a snapshots checkout."""
import json
import pathlib

from tinseltown.fetch import Page
from tinseltown.snapshot import slug


class SnapshotFetcher:
    def __init__(self, *roots):
        self.roots = [pathlib.Path(r) for r in roots]

    def page(self, url, scroll=True):
        for root in self.roots:
            d = root / slug(url)
            if (d / "page.html").exists():
                responses = []
                for f in sorted(d.glob("xhr-*.json")):
                    r = json.loads(f.read_text())
                    responses.append((r["url"], r["body"]))
                meta = json.loads((d / "meta.json").read_text())
                return Page(url, meta.get("status"), (d / "page.html").read_text(),
                            (d / "page.txt").read_text(), responses)
        raise LookupError(f"no snapshot for {url}")

    def get_json(self, url):
        raise LookupError("snapshots hold no direct API calls")
