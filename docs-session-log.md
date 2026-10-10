# Inskip Fishing Scanner — Session log, 10 October 2026

**Live:** https://colehenderson1985-web.github.io/inskip-fishing-scanner/ · **Repo:** https://github.com/colehenderson1985-web/inskip-fishing-scanner · **Version:** 0.3.0 · **Cost:** $0/month

## What happened today (11:14 → 14:09 AEST)

| Time | Milestone |
|---|---|
| 11:14 | Brief reviewed; v2 brief written (MVP defined, defaults set, budget $0 / approve >AUD 10/mo) |
| 11:25 | Stage 1 research: data sources confirmed, regulations verified, report layer assessed as thin |
| 11:45 | Stage 2 architecture: static site + GitHub Actions pipeline, config-driven locations/species/rules, Report Inbox via GitHub issues |
| 11:50–12:25 | Stage 3 build; repo created by Cole; GitHub App installed; four live runs fixed real source issues; Pages enabled; **site live** |
| 13:01 | Design review loop (3 passes) → v0.2.0: hero + tide ribbon, cards, chips, dawn theme |
| 13:17 | WhatsApp: one-tap share button; ntfy push notifications built (morning brief 04:30, evening preview 17:00 if ≥70) |
| 13:31 | Gardiner's Tackle World: Facebook not readable/automatable; their Shopify blog feed added as a source; report-vs-guide classification |
| 13:51 | Article cross-reference (BNB / Fishing World / Fishing Monthly): nothing current; sourced tide rules extracted |
| 14:06 | **v0.3.0 live**: score separation, environment-specific tide prefs, SST factor, sentence-level evidence pairing |

## Decisions recorded
- Environment-first scoring; public reports are a confidence modifier; group ratings are the long-term calibration source.
- Facebook: no automation (ToS/ban risk). Manual paste via More → Add a report; Claude can read pages in-session only unreliably.
- WhatsApp: no automated group posting exists safely. Chosen path = ntfy push to Cole + one-tap "Share to WhatsApp".
- BOM app API (`api.weather.bom.gov.au`) not used — its terms forbid it. Anonymous FTP + Open-Meteo instead.
- Tide data: MSQ open data (CC BY 4.0, confirmed) via CKAN datastore. Inskip tides estimated from Noosa Head / Tin Can Bay and labelled.
- Scores are suitability ratings; calibration curve: raw 0.95 → 100, 0.80 → 73, 0.65 → 45; cap 55 if any fundamental < 0.35.

## Still to do by Cole
- Add the GitHub secret `NTFY_TOPIC` = `inskip-scanner-6285b01cca2d` (Settings → Secrets → Actions) and subscribe to that topic in the ntfy app. Until then the pipeline skips the push step silently.
- Fish, then tap *Rate a session* (More tab). 20–30 ratings unlock the first weight retune.
- Optional: ask Gardiner's / The Chandlery to email their weekly report.

## Sources now polled daily
Open-Meteo forecast + marine · MSQ/BOM tides (Noosa Head, Tin Can Bay) · BOM coastal waters (K'gari Coast, Sunshine Coast Waters) + Double Island Point AWS via FTP · QPWS park alerts RSS · GSMP zones (quarterly) · Coastwatch weekly (TCB / Hervey Bay / Noosa sections) · Fisho's Tackle World Atom · Gardiner's Tackle World blog Atom · Noosa Today RSS (blocked, kept for when it returns)

## Next session suggestions
1. First calibration review once ratings exist (factor-disagreement table).
2. Validate Inskip bay-side tide offset against the water.
3. "What changed since yesterday" on Home.
4. Consider BNB archive mining (≈25 Tin Can Bay columns 2020–25) for species-by-month priors.
