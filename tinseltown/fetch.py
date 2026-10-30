"""Load venue pages in a headless browser, keeping the JSON the page requests."""
from dataclasses import dataclass, field
import json

from playwright.sync_api import sync_playwright, Error as PlaywrightError

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")


@dataclass
class Page:
    url: str
    status: int | None
    html: str
    text: str
    responses: list[tuple[str, str]] = field(default_factory=list)

    def json(self, url_part: str):
        """Body of the largest JSON response whose URL contains url_part."""
        bodies = [body for url, body in self.responses if url_part in url]
        if not bodies:
            raise LookupError(f"no response matching {url_part!r} on {self.url}")
        return json.loads(max(bodies, key=len))


class PageFetcher:
    def __enter__(self):
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch()
        self._context = self._browser.new_context(user_agent=UA, locale="en-US",
                                                  timezone_id="America/Los_Angeles")
        self._cache: dict[str, Page] = {}
        return self

    def __exit__(self, *exc):
        self._browser.close()
        self._pw.stop()

    def get_json(self, url: str):
        """Fetch a JSON endpoint directly, sharing the browser's cookies."""
        resp = self._context.request.get(url, timeout=60_000)
        if not resp.ok:
            raise RuntimeError(f"{url} returned HTTP {resp.status}")
        return resp.json()

    def page(self, url: str, scroll: bool = True) -> Page:
        if url in self._cache:
            return self._cache[url]
        responses: list[tuple[str, str]] = []

        def on_response(resp):
            if "json" in resp.headers.get("content-type", ""):
                try:
                    responses.append((resp.url, resp.text()))
                except Exception:
                    pass

        page = self._context.new_page()
        page.on("response", on_response)
        try:
            resp = page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            try:
                page.wait_for_load_state("networkidle", timeout=20_000)
            except PlaywrightError:
                pass  # some sites never go idle; take what has loaded
            if scroll:
                for _ in range(4):
                    page.mouse.wheel(0, 4000)
                    page.wait_for_timeout(400)
            result = Page(url, resp.status if resp else None, page.content(),
                          page.inner_text("body"), responses)
        finally:
            page.close()
        if result.status and result.status >= 400:
            raise RuntimeError(f"{url} returned HTTP {result.status}")
        self._cache[url] = result
        return result
