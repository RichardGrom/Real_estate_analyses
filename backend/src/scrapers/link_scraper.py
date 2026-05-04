import json
import logging
import re
import subprocess
import urllib.parse
import urllib.request
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

COOKIE_SELECTORS = [
    "#didomi-notice-agree-button",
    ".fc-cta-consent",
    "button[id*='accept']",
    "button:has-text('Aceptar')",
    "button:has-text('Accept')",
]

EXTRACTION_PROMPT = """Extract property listing data from the text below and return ONLY valid JSON.
Use null for any field you cannot find.

Required fields:
- price_eur: integer (sale price in euros)
- size_m2: integer (area in square metres)
- rooms: integer (number of bedrooms)
- bathrooms: integer
- address: string (full address or location description)
- lat: float (GPS latitude) or null
- lng: float (GPS longitude) or null
- has_terrace: boolean
- has_parking: boolean
- floor: string (e.g. "3rd floor", "ground floor", "penthouse") or null
- description: string (first 300 chars of property description)

Return only the JSON object, no markdown, no explanation.

TEXT:
{text}
"""


class ScraperError(Exception):
    pass


class LinkScraper:
    def scrape(self, url: str) -> dict:
        page_text, geo = self._fetch_page(url)
        if len(page_text) < 200:
            raise ScraperError(f"blocked: page text too short ({len(page_text)} chars)")
        data = self._extract(page_text)
        if geo:
            data["lat"] = geo["lat"]
            data["lng"] = geo["lng"]
        elif not data.get("lat") and data.get("address"):
            data["lat"], data["lng"] = self._geocode(data["address"])
        data["id"] = self._listing_id(url)
        data["url"] = url
        return data

    def _fetch_page(self, url: str) -> tuple[str, dict | None]:
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
            page_text = page.evaluate("document.body.innerText")
            geo = self._extract_geo_from_page(page)
            browser.close()
        return page_text, geo

    def _dismiss_cookies(self, page) -> None:
        for selector in COOKIE_SELECTORS:
            try:
                btn = page.locator(selector).first
                if btn.is_visible(timeout=1000):
                    btn.click()
                    page.wait_for_timeout(1500)
                    break
            except Exception:
                continue

    def _extract_geo_from_page(self, page) -> dict | None:
        try:
            return page.evaluate("""() => {
                for (const el of document.querySelectorAll('script[type="application/ld+json"]')) {
                    try {
                        const d = JSON.parse(el.textContent);
                        const objs = Array.isArray(d) ? d : [d];
                        for (const o of objs) {
                            if (o.geo) return {lat: o.geo.latitude, lng: o.geo.longitude};
                            if (o.location && o.location.geo)
                                return {lat: o.location.geo.latitude, lng: o.location.geo.longitude};
                        }
                    } catch {}
                }
                for (const el of document.querySelectorAll('script:not([src])')) {
                    const m = el.textContent.match(
                        /"latitude"\\s*:\\s*([\\d.\\-]+)[\\s\\S]{0,50}"longitude"\\s*:\\s*([\\d.\\-]+)/
                    );
                    if (m) return {lat: parseFloat(m[1]), lng: parseFloat(m[2])};
                }
                return null;
            }""")
        except Exception:
            return None

    def _extract(self, page_text: str) -> dict:
        prompt = EXTRACTION_PROMPT.format(text=page_text[:8000])
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            raise ScraperError(f"extraction_failed: {result.stderr[:200]}")
        raw = result.stdout.strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                return json.loads(match.group())
            raise ScraperError("extraction_failed: could not parse JSON from claude output")

    def _geocode(self, address: str) -> tuple[float | None, float | None]:
        try:
            encoded = urllib.parse.quote(address)
            req = urllib.request.Request(
                f"https://nominatim.openstreetmap.org/search?q={encoded}&format=json&limit=1",
                headers={"User-Agent": "re-investment-advisor/1.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            if data:
                return round(float(data[0]["lat"]), 6), round(float(data[0]["lon"]), 6)
        except Exception as exc:
            logger.warning("Nominatim geocoding failed: %s", exc)
        return None, None

    def _listing_id(self, url: str) -> str:
        return re.sub(r'^https?://', '', url).rstrip('/')
