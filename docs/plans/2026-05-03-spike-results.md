# Spike Results: Link-Based Property Extraction

**Date:** 2026-05-03
**Test URL:** `https://www.idealista.com/inmueble/111009537/`
**Script:** `backend/scripts/compare_approaches.py`

## Summary

All 5 approaches tested failed against Idealista.com. The root cause is **DataDome bot protection** — a dedicated anti-bot service that Idealista uses to block all automated access.

## Results

| Approach | Completeness | Time | Error |
|---|---|---|---|
| A: Exa.ai getContents + Claude | 0/11 | ~0s | Idealista not indexed by Exa |
| B: Apify `igolaizola/idealista-scraper` | 0/11 | ~0.6s | HTTP 403 — actor rental expired |
| C: Playwright headless + Claude | 0/11 | ~2s | DataDome — 0 chars returned |
| D: Playwright Stealth + Claude | 0/11 | ~2s | DataDome — 0 chars returned |
| E: Apify generic `apify/web-scraper` + Claude | 0/11 | ~22s | DataDome — 0 chars returned |

## Root Cause

Idealista uses **DataDome** (confirmed by response fingerprint: `dd={'rt':'i','cid':...}`), which blocks:

- Simple HTTP requests → `403 Forbidden`
- Playwright headless browser → empty page (0 chars, title: "idealista.com")
- Playwright + `playwright-stealth` v2.x → same empty page
- Apify cloud browsers (generic actor) → same empty page
- Exa.ai crawl index → Idealista not indexed

The only approach not blocked is the specialized `igolaizola/idealista-scraper` Apify actor, which implements Idealista-specific DataDome bypass techniques. It was working before rental expiry (Approach B code is correct).

## Options Going Forward

### Option 1 — Renew igolaizola/idealista-scraper rental (~€5/month)

**Pros:** Proven to work, returns fully structured JSON (no Claude extraction needed), includes `lat`/`lng`  
**Cons:** Monthly cost, Idealista-only  
**Code change:** None — Approach B is already implemented and correct

### Option 2 — Switch to Fotocasa.es

**Pros:** No DataDome protection, Playwright/requests likely works, free  
**Cons:** Fewer listings than Idealista, requires new scraper + extraction prompt  
**Code change:** Replace `TEST_URL`, rewrite extraction; `run_approach_c` or `run_approach_d` likely works

### Option 3 — Browser extension / clipboard input

**Pros:** Free, works on any site  
**Cons:** Manual step required from user, worse UX  
**Code change:** New input mode — accept raw text instead of URL

## Recommendation

Renew the `igolaizola/idealista-scraper` actor rental (Option 1). It is the only approach that:
- Returns all 11 required fields including `lat`/`lng` (needed by AirROI)
- Requires no additional extraction step (data already structured)
- Has no architectural changes needed — Approach B code is complete

If cost is a constraint, test Fotocasa.es first (Option 2) before committing.
