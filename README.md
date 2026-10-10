# Inskip Fishing Scanner

Daily fishing intelligence for Inskip Point, Rainbow Beach, Tin Can Bay and Double Island Point (Queensland).
Where, what and when — with the evidence and the rules.

**Live:** https://colehenderson1985-web.github.io/inskip-fishing-scanner/

## How it works
- `pipeline/` (Python) runs daily at 04:30 AEST on GitHub Actions: fetches weather and swell (Open-Meteo), official tide
  predictions (MSQ / BOM, CC BY 4.0), BOM coastal forecasts and warnings, QPWS park alerts, marine-park zones and public
  fishing reports; scores every location × species × window; writes `data/latest.json`.
- `site/` (Vite + React + MapLibre) is a static dashboard that reads `data/latest.json`, deployed to GitHub Pages on every push.
- `config/` holds the local knowledge: locations (aspect, shelter, tide reference, zone, access), species (season, tide and
  light preferences, legal limits), rules (closures, zones, permits, safety caps) and sources.
- `data/` separates raw payloads, verified observations, derived scores and the published `latest.json`.

Scores are **suitability ratings (0–100)**, not catch probabilities. Safety and legal restrictions override scores.

## Report Inbox
Open the site → More → *Add a report*, paste a shop's Facebook post or a mate's message, and submit. It opens a pre-filled
GitHub issue (label `report`); the inbox workflow files it as a dated, credited observation and re-scores.
*Rate a session* works the same way and is what calibrates the model over time.

## Run locally
```
pip install -r pipeline/requirements.txt
cd pipeline && python -m scanner.run refresh          # live fetch
python tests/synth.py && python -m scanner.run refresh --offline   # synthetic data, no network
python -m pytest -q
cd ../site && npm ci && npm run dev
```

## Operations
- Manual refresh: Actions → *Daily refresh* → Run workflow.
- Failures open/append a GitHub issue labelled `pipeline`; the dashboard shows stale feeds.
- Tide files are yearly; December runs fetch the next year automatically.
- Costs: $0 (GitHub free tier, Open-Meteo non-commercial, open government data).
