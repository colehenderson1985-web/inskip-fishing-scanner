# Changelog

## 0.3.1 — 2026-10-12
- Fix: the daily refresh now publishes to the site. Refreshed data was being committed but never deployed
  (pushes made by the workflow token do not trigger the Deploy workflow), so the site stayed on the last manual deploy.
- Schedules moved off :00/:30 (04:17 and 16:47 AEST) because GitHub was starting them 3–6 hours late.

## 0.3.0 — 2026-10-10
- Score separation: steeper calibration curve (raw 0.95 → 100, 0.80 → 73, 0.65 → 45), more demanding wind/swell/tide/light
  factors, and a cap when any fundamental (tide, wind, swell) is poor. Real-data spread now 40–100, median ~76.
- Environment-specific tide preferences per species, sourced from Fishing Monthly / Bush 'n Beach guides
  (whiting: low tide on the surf, flood on the flats; dart on the high; flathead on the fall; mulloway on a high near dark).
- Water-temperature factor for warm-water species (jack, mackerel, cobia).
- Sentence-level species↔location pairing in report extraction; reports classified as report vs guide (guides carry no evidence weight).
- New source: Gardiner's Tackle World blog (Shopify Atom feed). Push notifications via ntfy with WhatsApp share action.

## 0.2.0 — 2026-10-10
- Visual redesign: sea-ink hero with the tide ribbon inside it, stat row, score chips, white cards on a soft ground,
  styled controls, refined tab bar, dawn (dark) theme tokens.
- Species scanner ranks from all scored windows (every species gets a score), short species names in prose,
  compact source credits, cleaner daily brief wording.
- Tuning: shoulder season 0.5 / off-season 0.15 to spread scores; offline refresh reuses previous health correctly.

## 0.1.0 — 2026-10-10
- Initial pipeline: Open-Meteo weather/marine, MSQ tide CSVs (with modelled fallback), astral sun/moon,
  QPWS park alerts RSS, BOM coastal-waters forecast + Double Island Point observations via anonymous FTP,
  Coastwatch / Fisho's / Noosa Today report ingestion, Report Inbox for admin-submitted posts.
- Deterministic suitability scoring (gate → 9 factors → environment-specific weights → windows → explanation).
- Config-driven locations (9), species (12), rules (closures, zones, permits, safety caps).
- 16 tests incl. offline end-to-end determinism.
