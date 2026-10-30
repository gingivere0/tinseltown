"""Save each venue page's HTML, text, and JSON responses, for writing and debugging parsers.

python -m tinseltown.snapshot OUT_DIR [URL ...]

With no URLs, every page in venues.yaml is saved.
"""
import json
import pathlib
import re
import sys

import yaml
from playwright.sync_api import sync_playwright, Error as PlaywrightError

from .fetch import UA

ROOT = pathlib.Path(__file__).resolve().parent.parent
MAX_BODY = 3_000_000


def slug(url: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", url.lower().split("//", 1)[-1]).strip("-")[:80]


def main(out_dir: str, urls: list[str]) -> None:
    out = pathlib.Path(out_dir)
    if not urls:
        venues = yaml.safe_load((ROOT / "venues.yaml").read_text())
        urls = list(dict.fromkeys(u for v in venues for u in v["urls"]))
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(user_agent=UA, locale="en-US", timezone_id="America/Los_Angeles")
        for url in urls:
            d = out / slug(url)
            d.mkdir(parents=True, exist_ok=True)
            responses = []

            def on_response(resp, responses=responses):
                ctype = resp.headers.get("content-type", "")
                if "json" in ctype or resp.request.resource_type in ("xhr", "fetch"):
                    try:
                        body = resp.text()
                    except Exception:
                        return
                    responses.append({"url": resp.url, "status": resp.status, "type": ctype,
                                      "body": body[:MAX_BODY]})

            page = context.new_page()
            page.on("response", on_response)
            meta = {"url": url}
            try:
                r = page.goto(url, wait_until="domcontentloaded", timeout=60_000)
                meta["status"] = r.status if r else None
                try:
                    page.wait_for_load_state("networkidle", timeout=20_000)
                except PlaywrightError:
                    pass
                for _ in range(6):
                    page.mouse.wheel(0, 4000)
                    page.wait_for_timeout(500)
                meta["final_url"] = page.url
                (d / "page.html").write_text(page.content())
                (d / "page.txt").write_text(page.inner_text("body"))
            except Exception as exc:
                meta["error"] = f"{type(exc).__name__}: {exc}"
            finally:
                page.close()
            for i, resp in enumerate(responses):
                (d / f"xhr-{i:02d}.json").write_text(json.dumps(resp, indent=1))
            meta["xhr"] = [{"i": i, "url": r["url"], "status": r["status"], "bytes": len(r["body"])}
                           for i, r in enumerate(responses)]
            (d / "meta.json").write_text(json.dumps(meta, indent=1))
            print(url, meta.get("status"), meta.get("error", ""), len(responses), "xhr", flush=True)
        browser.close()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
