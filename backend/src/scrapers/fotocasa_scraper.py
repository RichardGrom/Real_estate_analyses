import json
import logging
import re
import subprocess

from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

COOKIE_SELECTORS = [
    "#didomi-notice-agree-button",
    ".fc-cta-consent",
    "button[id*='accept']",
    "button:has-text('Aceptar')",
    "button:has-text('Accept')",
]

EXTRACT_RENTALS_PROMPT = """Extract rental listing data from this Spanish real estate website text.
Return ONLY a valid JSON array. Each item must have:
- price: integer (monthly rent in euros)
- size_m2: integer (area in square metres)

Include only listings where BOTH price AND size are clearly stated.
Return [] if no clear rental listings found.
Return only the JSON array, no markdown, no explanation.

TEXT:
{text}
"""


class FotocasaScraper:
    def scrape_rentals(self, location: str, max_items: int = 30) -> list[dict]:
        url = self._build_url(location)
        logger.info("FotocasaScraper | url=%s", url)
        page_text = self._fetch_page(url)
        if len(page_text) < 200:
            raise RuntimeError(f"Fotocasa blocked (page text: {len(page_text)} chars)")
        return self._extract_listings(page_text)[:max_items]

    def _build_url(self, location: str) -> str:
        slug = location.lower().strip().replace(" ", "-").replace(",", "")
        return f"https://www.fotocasa.es/es/alquiler/casas/{slug}-capital/todas-las-zonas/l"

    def _fetch_page(self, url: str) -> str:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/124.0.0.0 Safari/537.36"
            )
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(2000)
            self._dismiss_cookies(page)
            text = page.evaluate("document.body.innerText")
            browser.close()
        return text

    def _dismiss_cookies(self, page) -> None:
        for selector in COOKIE_SELECTORS:
            try:
                btn = page.locator(selector).first
                if btn.is_visible(timeout=1000):
                    btn.click()
                    page.wait_for_timeout(1000)
                    break
            except Exception:
                continue

    def _extract_listings(self, page_text: str) -> list[dict]:
        prompt = EXTRACT_RENTALS_PROMPT.format(text=page_text[:8000])
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            raise RuntimeError(f"claude -p failed: {result.stderr[:200]}")
        raw = result.stdout.strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r'\[.*\]', raw, re.DOTALL)
            if match:
                return json.loads(match.group())
            return []
