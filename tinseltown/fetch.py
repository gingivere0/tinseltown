"""Render venue pages in a headless browser and return their visible text."""
from playwright.sync_api import sync_playwright, Error as PlaywrightError

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
MAX_CHARS = 120_000


class PageFetcher:
    def __enter__(self):
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch()
        self._context = self._browser.new_context(user_agent=UA, locale="en-US",
                                                  timezone_id="America/Los_Angeles")
        return self

    def __exit__(self, *exc):
        self._browser.close()
        self._pw.stop()

    def text(self, url: str) -> str:
        page = self._context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            try:
                page.wait_for_load_state("networkidle", timeout=20_000)
            except PlaywrightError:
                pass  # some sites never go idle; take what has rendered
            # Scroll to trigger lazy-loaded calendars.
            for _ in range(6):
                page.mouse.wheel(0, 4000)
                page.wait_for_timeout(500)
            body = page.inner_text("body")
            return body[:MAX_CHARS]
        finally:
            page.close()
