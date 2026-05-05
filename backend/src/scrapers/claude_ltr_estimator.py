import json
import logging
import re
import subprocess

logger = logging.getLogger(__name__)

ESTIMATION_PROMPT = """You are a Spanish real estate market expert.

Estimate the average monthly rental price for a {size_m2}m2 apartment in {location}, Spain.

Return ONLY valid JSON (no markdown, no explanation):
{{
  "avg_monthly_rent_eur": <integer>,
  "rent_per_m2_month": <float, 2 decimals>,
  "confidence": "<high|medium|low>",
  "notes": "<one-sentence explanation of estimate basis>"
}}

Base your estimate on 2024-2025 market conditions."""


class ClaudeLTREstimator:
    def estimate(self, location: str, size_m2: int) -> dict:
        prompt = ESTIMATION_PROMPT.format(location=location, size_m2=size_m2)
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True, text=True, timeout=60,
            stdin=subprocess.DEVNULL,
        )
        if result.returncode != 0:
            raise RuntimeError(f"claude -p failed: {result.stderr[:200]}")
        return self._parse(result.stdout.strip())

    def _parse(self, raw: str) -> dict:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                return json.loads(match.group())
            raise RuntimeError(f"Could not parse JSON: {raw[:200]}")
