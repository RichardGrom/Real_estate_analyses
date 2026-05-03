"""
Spike: compare 3 property extraction approaches on a single Idealista URL.
Run: uv run python scripts/compare_approaches.py
"""
import json
import sys
import time
from dataclasses import dataclass, field

TEST_URL = "https://www.idealista.com/inmueble/111009537/"
FIELDS = ["price_eur", "size_m2", "rooms", "bathrooms",
          "address", "lat", "lng", "has_terrace", "has_parking",
          "floor", "description"]

EXTRACTION_PROMPT = """
Extract property listing data from the text below and return ONLY valid JSON.
Use null for any field you cannot find.

Required fields:
- price_eur: integer (sale price in euros)
- size_m2: integer (area in square metres)
- rooms: integer (number of bedrooms)
- bathrooms: integer
- address: string (full address or location description)
- lat: float (GPS latitude, e.g. 36.51)
- lng: float (GPS longitude, e.g. -4.88)
- has_terrace: boolean
- has_parking: boolean
- floor: string (e.g. "2nd floor", "ground floor", "penthouse")
- description: string (first 300 chars of property description)

Return only the JSON object, no markdown, no explanation.

TEXT:
{text}
"""


@dataclass
class ApproachResult:
    name: str
    data: dict = field(default_factory=dict)
    elapsed_s: float = 0.0
    cost_usd: float = 0.0
    error: str | None = None

    def completeness(self) -> int:
        return sum(1 for f in FIELDS if self.data.get(f) is not None)


def print_results(results: list[ApproachResult]) -> None:
    print("\n" + "=" * 70)
    print(f"{'FIELD':<20}", end="")
    for r in results:
        print(f"{r.name:<22}", end="")
    print()
    print("-" * 70)
    for f in FIELDS:
        print(f"{f:<20}", end="")
        for r in results:
            val = r.data.get(f)
            cell = str(val)[:18] if val is not None else "✗ null"
            print(f"{cell:<22}", end="")
        print()
    print("-" * 70)
    print(f"{'Completeness':<20}", end="")
    for r in results:
        print(f"{r.completeness()}/{len(FIELDS):<19}", end="")
    print()
    print(f"{'Time (s)':<20}", end="")
    for r in results:
        print(f"{r.elapsed_s:.1f}s{'':<19}", end="")
    print()
    print(f"{'Est. cost':<20}", end="")
    for r in results:
        print(f"${r.cost_usd:.4f}{'':<16}", end="")
    print()
    print(f"{'Error':<20}", end="")
    for r in results:
        err = (r.error or "none")[:20]
        print(f"{err:<22}", end="")
    print()
    print("=" * 70)


def run_approach_a(url: str) -> ApproachResult:
    """Exa.ai getContents → Claude CLI extraction (subscription auth)."""
    import subprocess
    from exa_py import Exa
    from src.config import Config

    cfg = Config()
    t0 = time.time()
    try:
        exa = Exa(api_key=cfg.exa_api_key)
        contents = exa.get_contents([url], text=True)
        page_text = contents.results[0].text if contents.results else ""
        if not page_text:
            return ApproachResult("A: Exa+Claude", error="Exa returned empty text")

        prompt = EXTRACTION_PROMPT.format(text=page_text[:8000])
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            return ApproachResult("A: Exa+Claude", elapsed_s=round(time.time() - t0, 1),
                                   error=f"claude CLI error: {result.stderr[:80]}")
        raw = result.stdout.strip()
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:-1])
        data = json.loads(raw)

        return ApproachResult("A: Exa+Claude", data=data,
                               elapsed_s=round(time.time() - t0, 1), cost_usd=0.0)
    except Exception as exc:
        return ApproachResult("A: Exa+Claude", elapsed_s=round(time.time() - t0, 1), error=str(exc)[:80])


if __name__ == "__main__":
    print(f"Testing URL: {TEST_URL}\n")
    results = []
    print("Running Approach A (Exa + Claude)...")
    results.append(run_approach_a(TEST_URL))
    print_results(results)
