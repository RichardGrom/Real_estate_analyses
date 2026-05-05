# How This Project Was Built — Vibe Coding with Claude Code

## What is Vibe Coding?

Vibe coding is a development approach where a human collaborates with an AI assistant (here: **Claude Code**) to build software iteratively. The human defines the goal, makes decisions, and steers the direction — the AI writes code, suggests solutions, and implements changes in response to natural-language instructions.

The full conversation history between me and Claude Code is not stored in git, but the **process is traceable** through the commit history, design documents in `docs/plans/`, and the code itself.

---

## My Role vs. Claude Code's Role

| What I (human) did | What Claude Code did |
|---|---|
| Defined the product goal and use case | Wrote all Python and TypeScript code |
| Chose which data sources to use | Designed module structure and class interfaces |
| Approved or rejected design proposals | Generated unit tests (TDD-first) |
| Decided when a design wasn't working | Debugged failures and fixed edge cases |
| Steered pivots (e.g. away from Idealista) | Refactored code on request |
| Reviewed results and gave feedback | Documented decisions in design docs |

---

## The Development Process, Step by Step

### Step 1 — Starting Simple (commits: `57c145e` → `0c30c0f`)

I started with a clear goal: *"I want to know if a property in Spain is worth buying as a short-term or long-term rental."*

I gave Claude Code the initial brief and it scaffolded the first version: three analyzers (capital growth via INE API, ROI calculator, property filter), then a complete React frontend with STR/LTR columns and a yield chart.

Everything was wired together with a FastAPI backend. At this point the user still had to fill in 8 form fields manually.

**My instruction at this stage was roughly:**
> "Build a tool that takes property parameters and returns rental yields and a capital growth estimate. Use INE data for growth. React frontend."

---

### Step 2 — Rethinking the Input (design pivot)

The 8-field form felt clunky. I asked Claude Code:
> "What if the user just pastes a URL to a listing instead of filling in fields?"

Claude Code produced a design document (`docs/plans/2026-05-03-link-based-analysis-design.md`) comparing three extraction approaches and recommending a spike test before committing.

I approved the spike test approach — we didn't write production code until we knew what worked.

---

### Step 3 — Spike Tests: Failing Fast (commits: `c3ef75e` → `1064595`)

Five different scraping approaches were tested on a real Idealista.com URL:

| Approach | Tool | Result |
|---|---|---|
| A | Exa.ai + Claude | Blocked — Idealista not indexed |
| B | Apify Idealista actor | Blocked — actor rental expired |
| C | Playwright headless + Claude | Blocked — DataDome returned 0 chars |
| D | Playwright + stealth | Blocked — same |
| E | Apify generic scraper + Claude | Blocked — same |

**Every approach failed.** The spike results are documented in `docs/plans/2026-05-03-spike-results.md`.

This was a real technical dead end. I decided: *switch away from Idealista to Fotocasa.es*, which has no DataDome protection. Claude Code updated the scraper and extraction prompt — and it worked: **10 out of 11 fields extracted reliably**.

---

### Step 4 — Building the Link-Based Pipeline (commits: `8865f41` → `b206c7a`)

With the scraping approach validated, Claude Code implemented the full link-based pipeline following a TDD approach:

1. Write test first
2. Watch it fail
3. Implement the feature
4. Make the test pass

Key components built in this phase:
- `LinkScraper` — Playwright + `claude -p` subprocess + Nominatim geocoding
- `pipeline.py` — orchestrates scraper + 3 parallel analyzers
- New API endpoint `POST /api/analysis {url}` replacing the old form

I gave specific feedback throughout, for example:
> "Remove the BUY/WATCH/SKIP verdict — I want the user to see raw numbers and decide themselves."

Claude Code removed the `verdict` field from `ROIAnalyzer` and updated all downstream models.

---

### Step 5 — LTR Estimation: Comparing Options (commits: `3745749` → `d7632a4`)

For long-term rental estimates I needed a data source. Claude Code proposed two options:

- **Option A:** Use `claude -p` to estimate rent based on location + property attributes (free, AI-only)
- **Option C:** Scrape Fotocasa rental listings via Playwright + `claude -p` extraction

A comparison script was built and run on real data. Option A was accurate enough and much simpler. I chose it. Claude Code integrated `ClaudeLTREstimator` into `LTRAnalyzer`.

---

### Step 6 — Debugging Real Failures

Several bugs were found only when running the full pipeline end-to-end. Claude Code identified and fixed each one:

**Bug: silent hang in subprocess**  
`claude -p` CLI waits 3 seconds for stdin when called inside a thread, causing LTR to silently return N/A. Fix: add `stdin=subprocess.DEVNULL` to all subprocess calls.

**Bug: `None` address caused crash**  
`listing.get("address", "")` returns `None` when the key exists but is null. Fix: use `listing.get("address") or ""`.

**Bug: cryptic `TypeError` when price is missing**  
Replaced with an explicit `ValueError("price_eur is missing from listing")`.

These are documented in `CLAUDE.md` under *Known Bugs Fixed*.

---

### Step 7 — Cleanup and Removal (commits: `41d3118` → `dd73d6e`)

At the end, I asked Claude Code to clean up:
- Remove outdated multi-agent planning docs
- Remove analysis output files
- Exclude `.claude/` settings and `0_instructions/` from git

This left the repository in a clean, presentable state.

---

## What the Git History Shows

The 56 commits follow a consistent pattern that reflects real iterative development:

```
docs:    planning and design decisions written before code
spike:   experimental scripts to validate technical assumptions
feat:    new features added after validation
fix:     bugs found during real testing
refactor: design pivots based on my feedback
chore:   dependencies, tooling, cleanup
```

This is not a project written all at once. It evolved through real decisions, real failures, and real pivots — all of which are visible in the git log.

---

## Tools Used

| Tool | Purpose |
|---|---|
| **Claude Code** (CLI) | Main AI coding assistant — wrote all code |
| **`claude -p`** (subprocess) | Used inside the app itself for AI extraction |
| **Playwright** | Headless browser for scraping listing pages |
| **AirROI API** | Short-term rental revenue estimates |
| **INE REST API** | Spanish housing price index (capital growth) |
| **Nominatim / OpenStreetMap** | Geocoding — address → latitude/longitude |
| **FastAPI + React + Vite** | Backend and frontend framework |
| **pytest** | 29 tests, all passing |
