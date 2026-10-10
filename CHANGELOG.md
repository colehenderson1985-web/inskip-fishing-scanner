# Changelog

## 0.1.0 — 2026-10-10
- Initial pipeline: Open-Meteo weather/marine, MSQ tide CSVs (with modelled fallback), astral sun/moon,
  QPWS park alerts RSS, BOM coastal-waters forecast + Double Island Point observations via anonymous FTP,
  Coastwatch / Fisho's / Noosa Today report ingestion, Report Inbox for admin-submitted posts.
- Deterministic suitability scoring (gate → 9 factors → environment-specific weights → windows → explanation).
- Config-driven locations (9), species (12), rules (closures, zones, permits, safety caps).
- 16 tests incl. offline end-to-end determinism.
