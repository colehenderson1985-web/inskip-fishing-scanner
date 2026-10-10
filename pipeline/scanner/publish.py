"""Build the daily brief, species scanner, health and latest.json."""
from __future__ import annotations

from datetime import datetime, timedelta

from . import __version__
from .util import iso, now


def brief(day: dict, ctx: dict, cfg: dict) -> dict:
    """Template-generated plain-English brief for a day (no LLM)."""
    locs = {l["id"]: l for l in cfg["locations"]["locations"]}
    sp = {s["id"]: s for s in cfg["species"]["species"]}
    top = day["top"]
    alerts = [a for a in ctx.get("alerts", []) if a.get("severity") in ("closure", "warning")]
    if not top:
        return {"outlook": "unknown", "headline": "No scored opportunities today.",
                "summary": "Forecast or tide data was unavailable, so no recommendations were generated. The last verified data is shown where available.",
                "best_location": None, "best_species": None, "windows": [], "confidence": "none", "warnings": [a["title"] for a in alerts]}
    best = top[0]
    scores = [r["score"] for r in top[:5]]
    avg = sum(scores) / len(scores)
    outlook = "good" if avg >= 65 else "fair" if avg >= 50 else "poor"
    outlook_words = {"good": "Good day to be out", "fair": "Mixed — pick your window", "poor": "Tough conditions"}[outlook]
    c = best["conditions"]
    loc = locs[best["location"]]
    rel = c.get("wind_relation") or "variable"
    wind_phrase = f"{c.get('wind_dir') or ''} wind ~{c['wind_kn']} kn ({rel} at {loc['short']})".strip()
    seas = f", seas ~{c['seas_m']} m" if c.get("seas_m") is not None else ""
    stage_word = {
        "low_turn": "bottom of the tide", "rising_early": "early run-in", "rising_late": "last of the run-in",
        "high_turn": "top of the tide", "falling_early": "start of the run-out", "falling_late": "last of the run-out",
    }.get(c.get("tide_stage") or "", "")
    windows = []
    seen = set()
    for r in top[:5]:
        key = (r["location"], r["window"]["start"])
        if key in seen:
            continue
        seen.add(key)
        windows.append({"location": locs[r["location"]]["short"], "species": sp[r["species"]]["name"],
                        "start": r["window"]["start"], "end": r["window"]["end"], "score": r["score"]})
    best_species_id = best["species"]
    with_reports = [r for r in top if r["evidence"]]
    rep_phrase = ""
    if with_reports:
        e = with_reports[0]["evidence"][0]
        rep_phrase = f" Recent reports ({e.get('credit') or e.get('source')}, {e['date']}) mention {sp[with_reports[0]['species']]['name'].lower()} around {locs[with_reports[0]['location']]['short']}."
    else:
        rep_phrase = " No recent public reports support today's picks — they rest on conditions and season."
    wind_phrase = wind_phrase[0].upper() + wind_phrase[1:]
    summary = (f"{wind_phrase}{seas}. Best bet is {sp[best['species']]['name'].lower()} at "
               f"{loc['short']} {best['window']['start']}–{best['window']['end']}"
               + (f" on the {stage_word}" if stage_word else "") + f" (suitability {best['score']}/100, {best['confidence']} confidence)."
               + rep_phrase)
    warn = [a["title"] for a in alerts][:4] + sorted({w for r in top[:5] for w in r["warnings"]})[:3]
    if ctx.get("marine_warning"):
        warn.insert(0, "BOM marine warning current — check the coastal waters forecast before heading out")
    return {
        "outlook": outlook, "headline": outlook_words,
        "summary": summary,
        "best_location": {"id": loc["id"], "name": loc["name"], "short": loc["short"], "score": best["score"]},
        "best_species": {"id": best_species_id, "name": sp[best_species_id]["name"]},
        "windows": windows[:4],
        "drivers": _drivers(best),
        "confidence": best["confidence"],
        "warnings": warn,
    }


def _drivers(r: dict) -> list[str]:
    f = r["factors"]
    labels = {"tide": "Tide stage", "wind": "Wind vs shore", "swell": "Swell/seas", "light": "Time of day",
              "season": "Season", "reports": "Recent reports", "pressure": "Pressure trend", "rain": "Rain/runoff", "lunar": "Moon"}
    ranked = sorted(f.items(), key=lambda kv: -kv[1])
    return [f"{labels[k]} ({'strong' if v >= .85 else 'ok' if v >= .6 else 'weak'})" for k, v in ranked[:4]]


def species_scanner(days: list[dict], ctx: dict, cfg: dict) -> list[dict]:
    locs = {l["id"]: l for l in cfg["locations"]["locations"]}
    out = []
    today = days[0]
    for s in cfg["species"]["species"]:
        rows = [r for d in days[:3] for r in d["top"] if r["species"] == s["id"]]
        # include all opportunities (not only top) for today for better ranking
        best_locs: dict[str, dict] = {}
        for r in rows:
            cur = best_locs.get(r["location"])
            if not cur or r["score"] > cur["score"]:
                best_locs[r["location"]] = {"location": r["location"], "name": locs[r["location"]]["short"], "score": r["score"],
                                            "window": r["window"], "date": r["window"]["start_iso"][:10]}
        ranked = sorted(best_locs.values(), key=lambda x: -x["score"])[:4]
        obs = [o for o in ctx["observations"] if s["id"] in o.get("species", [])]
        obs.sort(key=lambda o: o.get("report_date", ""), reverse=True)
        recent = [{"source": o.get("credit") or o.get("source_name"), "date": o.get("report_date"), "catch_date": o.get("catch_date"),
                   "url": o.get("url"), "provenance": o.get("provenance"), "locations": o.get("locations", []),
                   "excerpt": o.get("text", "")[:200]} for o in obs[:4]]
        month = ctx["today"].month
        season = "peak" if month in s["season"]["peak"] else "shoulder" if month in s["season"].get("shoulder", []) else "off"
        top_score = ranked[0]["score"] if ranked else None
        outlook = ("good" if top_score and top_score >= 65 else "fair" if top_score and top_score >= 45 else "poor") if top_score else "unknown"
        closures = []
        for cid in s.get("legal", {}).get("closures", []):
            c = next((x for x in cfg["rules"]["closures"] if x["id"] == cid), None)
            if c:
                from .score import closure_active
                closures.append({"name": c["name"], "active": closure_active(c, ctx["today"]), "source": c["source"]})
        out.append({
            "id": s["id"], "name": s["name"], "short": s.get("short", s["name"]), "outlook": outlook, "top_score": top_score,
            "season": season, "season_months": s["season"],
            "best_locations": ranked, "recent_reports": recent,
            "days_since_report": (ctx["today"].date() - datetime.strptime(obs[0]["report_date"], "%Y-%m-%d").date()).days if obs else None,
            "legal": s.get("legal", {}), "legal_note": s.get("legal_note"), "closure_note": s.get("closure_note"), "closures": closures,
            "techniques": s.get("techniques", []),
            "confidence": ranked and next((r["confidence"] for r in rows if r["location"] == ranked[0]["location"]), "low") or "none",
            "basis": "reports + conditions" if recent and any((ctx["today"].date() - datetime.strptime(r["date"], "%Y-%m-%d").date()).days <= 14 for r in recent) else "conditions + season",
        })
    out.sort(key=lambda x: -(x["top_score"] or 0))
    return out


def health(results: list[dict], sources_cfg: dict, prev: dict | None) -> dict:
    cats = {
        "weather": ["open_meteo_forecast"], "marine": ["open_meteo_marine"],
        "bom": ["bom_coastal", "bom_obs"], "tides": [r["source"] for r in results if r["source"].startswith("tides_")],
        "alerts": ["qpws_alerts"], "reports": ["coastwatch", "fishos", "noosa_today"], "map": ["gsmp_zones"],
    }
    by = {r["source"]: r for r in results}
    prev_src = (prev or {}).get("sources", {})
    out_src, stale = {}, []
    for cat, ids in cats.items():
        for sid in ids:
            r = by.get(sid)
            p = prev_src.get(sid, {})
            if r and r["ok"]:
                out_src[sid] = {"ok": True, "last_success": r["fetched_at"], "items": r["items"], "note": r.get("note"), "error": None, "category": cat}
            else:
                out_src[sid] = {"ok": False, "last_success": p.get("last_success"), "items": r["items"] if r else 0,
                                "error": (r or {}).get("error"), "category": cat, "stale": True}
                if cat in ("weather", "marine", "tides") and cat not in stale:
                    stale.append(cat)
    nxt = now().replace(hour=4, minute=30, second=0, microsecond=0)
    if nxt <= now():
        nxt += timedelta(days=1)
    return {"generated_at": iso(now()), "next_scheduled": iso(nxt), "sources": out_src, "stale_categories": stale,
            "overall": "ok" if not stale else "degraded"}


def build_latest(days: list[dict], briefs: list[dict], species: list[dict], ctx: dict, cfg: dict, hlth: dict) -> dict:
    locs = cfg["locations"]["locations"]
    obs = sorted(ctx["observations"], key=lambda o: o.get("report_date", ""), reverse=True)[:40]
    latest = {
        "generated_at": iso(now()),
        "timezone": "Australia/Brisbane",
        "region": cfg["locations"]["region"],
        "brief": briefs[0],
        "days": [{"date": d["date"], "brief": b, "astro": d["astro"], "top": d["top"], "locations": d["locations"]}
                 for d, b in zip(days, briefs)],
        "locations": [{k: v for k, v in l.items() if k != "species"} | {"species": l["species"]} for l in locs],
        "species": species,
        "reports": obs,
        "days_since_local_report": _days_since_local(obs, ctx["today"]),
        "alerts": ctx.get("alerts", []),
        "bom": {"coastal": ctx.get("bom_coastal", {}), "obs": (ctx.get("bom_obs") or {}).get("obs", [])[:12],
                "pressure_trend": ctx.get("pressure_trend"), "marine_warning": ctx.get("marine_warning")},
        "tides": {k: [r for r in v if ctx["today"].strftime("%Y-%m-%d") <= r["t"][:10] <= (ctx["today"] + timedelta(days=8)).strftime("%Y-%m-%d")]
                  for k, v in ctx["tides"].items()},
        "marine": {k: _slim(v) for k, v in ctx["marine"].items()},
        "weather": {k: _slim(v) for k, v in ctx["weather"].items()},
        "health": hlth,
        "rules": {"zones": cfg["rules"]["zones"], "permits": cfg["rules"]["permits"], "zones_source": cfg["rules"]["zones_source"],
                  "legal_source": cfg["species"]["legal_source"], "closures_source": cfg["species"]["closures_source"]},
        "attribution": [v.get("attribution") for v in cfg["sources"]["weather"].values() if v.get("attribution")]
                       + [cfg["sources"]["tides"]["msq"]["attribution"], "Park alerts © Queensland Parks and Wildlife Service"],
        "version": __version__,
    }
    return latest


def _slim(series: dict) -> dict:
    keep = ["time", "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m", "pressure_msl", "precipitation", "temperature_2m",
            "wave_height", "swell_wave_height", "swell_wave_direction", "swell_wave_period", "sea_surface_temperature", "name", "lat", "lon"]
    return {k: series[k] for k in keep if k in series}


def _days_since_local(obs: list[dict], today: datetime) -> int | None:
    for o in obs:
        if o.get("locations"):
            try:
                return (today.date() - datetime.strptime(o["report_date"], "%Y-%m-%d").date()).days
            except ValueError:
                continue
    return None
