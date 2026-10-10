"""CLI: `python -m scanner.run refresh` (daily) · `python -m scanner.run inbox payload.json`
`python -m scanner.run refresh --offline` scores from cached data without fetching (for tests/dev).
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import timedelta

from . import publish, score
from .ingest import astro as astro_mod, bom, inbox, open_meteo, qpws, reports, tides, zones
from .util import CACHE, DATA, DERIVED, load_config, log, now, read_json, today, write_json


def refresh(offline: bool = False, days: int = 7) -> dict:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = load_config()
    sources, rules = cfg["sources"], cfg["rules"]
    locs = cfg["locations"]["locations"]
    region = cfg["locations"]["region"]
    results = []
    t0 = today()

    if offline:
        weather = read_json(CACHE / "weather.json", {})
        marine = read_json(CACHE / "marine.json", {})
        tide_rows = {sid: read_json(CACHE / f"tides_{sid}_{t0.year}.json", []) for sid in sources["tides"]["msq"]["stations"]}
        alerts = read_json(CACHE / "alerts.json", [])
        coastal = read_json(CACHE / "bom_coastal.json", {})
        obs_bom = read_json(CACHE / "bom_obs.json", {})
        prev_health = read_json(DATA / "health.json", {})
        results = [v | {"source": k} for k, v in (prev_health.get("sources") or {}).items()]
    else:
        weather, r = open_meteo.fetch_weather(locs, days=days + 3); results.append(r)
        marine, r = open_meteo.fetch_marine(region["marine_points"], days=8); results.append(r)
        tide_rows, rs = tides.fetch_all(sources, marine); results += rs
        alerts, r = qpws.fetch_alerts(sources, rules); results.append(r)
        coastal, r = bom.fetch_coastal(sources, [z["name"] for z in region["bom_coastal_zones"]]); results.append(r)
        obs_bom, r = bom.fetch_obs(sources, region["obs_station"]["id"]); results.append(r)
        added, rs = reports.fetch_all(sources); results += rs
        log.info("reports: %d new observations", added)
        results.append(zones.fetch_zones(region["bbox"]))

    prev_health = read_json(DATA / "health.json", {})
    hlth = publish.health([dict(r) for r in results], sources, prev_health)

    ctx = {
        "config": cfg, "rules": rules, "today": t0,
        "weather": weather, "marine": marine, "tides": tide_rows, "alerts": alerts,
        "bom_coastal": coastal, "bom_obs": obs_bom,
        "pressure_trend": bom.pressure_trend((obs_bom or {}).get("obs", [])),
        "marine_warning": bool((coastal or {}).get("warning_active")),
        "observations": reports.load_observations(),
        "health": hlth,
        "astro": {},
    }
    lat, lon = locs[0]["centre"]
    for i in range(days + 1):
        d = t0 + timedelta(days=i)
        ctx["astro"][d.strftime("%Y-%m-%d")] = astro_mod.day_astro(d, lat, lon)

    day_results, briefs = [], []
    for i in range(days + 1):
        d = t0 + timedelta(days=i)
        try:
            sd = score.score_day(d, ctx)
        except Exception as e:  # noqa: BLE001
            log.exception("scoring failed for %s", d.date())
            hlth.setdefault("errors", []).append(f"scoring {d.date()}: {e}")
            sd = {"date": d.strftime("%Y-%m-%d"), "astro": ctx["astro"][d.strftime("%Y-%m-%d")], "top": [], "locations": {}, "all_count": 0}
        day_results.append(sd)
        briefs.append(publish.brief(sd, ctx, cfg))
    if hlth.get("errors"):
        hlth["overall"] = "degraded"
    species = publish.species_scanner(day_results, ctx, cfg)
    latest = publish.build_latest(day_results, briefs, species, ctx, cfg, hlth)

    write_json(DERIVED / f"{t0.strftime('%Y-%m-%d')}.json", {"days": day_results, "health": hlth, "generated_at": latest["generated_at"]})
    write_json(DATA / "latest.json", latest)
    write_json(DATA / "health.json", hlth)
    log.info("refresh complete: %s | top: %s", hlth["overall"],
             [(r["location"], r["species"], r["score"]) for r in day_results[0]["top"][:3]])
    return latest


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("refresh"); r.add_argument("--offline", action="store_true"); r.add_argument("--days", type=int, default=7)
    i = sub.add_parser("inbox"); i.add_argument("payload")
    a = ap.parse_args(argv)
    if a.cmd == "refresh":
        latest = refresh(offline=a.offline, days=a.days)
        print(json.dumps({"generated_at": latest["generated_at"], "overall": latest["health"]["overall"],
                          "top": [(x["location"], x["species"], x["score"]) for x in latest["days"][0]["top"][:5]]}, indent=1))
    elif a.cmd == "inbox":
        with open(a.payload, "r", encoding="utf-8") as f:
            payload = json.load(f)
        print(json.dumps(inbox.ingest_payload(payload), indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
