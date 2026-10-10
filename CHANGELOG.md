# Changelog

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
