"""Scoring engine: gate → factors → weighted suitability → windows → explanation.

Outputs suitability scores (0–100), NOT catch probabilities. Deterministic.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta

from . import model
from .ingest.astro import light_period
from .ingest.open_meteo import at

WEIGHTS = {
    "surf_beach":       {"tide": .22, "wind": .20, "swell": .15, "light": .13, "season": .12, "reports": .10, "pressure": .04, "rain": .02, "lunar": .02},
    "estuary":          {"tide": .28, "wind": .12, "swell": .03, "light": .15, "season": .14, "reports": .12, "pressure": .06, "rain": .08, "lunar": .02},
    "sheltered_strait": {"tide": .28, "wind": .12, "swell": .03, "light": .15, "season": .14, "reports": .12, "pressure": .06, "rain": .08, "lunar": .02},
    "headland":         {"tide": .22, "wind": .18, "swell": .18, "light": .12, "season": .12, "reports": .10, "pressure": .04, "rain": .02, "lunar": .02},
}

STAGE_WORDS = {
    "low_turn": "the bottom of the tide", "rising_early": "the early run-in", "rising_late": "the last of the run-in",
    "high_turn": "the top of the tide", "falling_early": "the start of the run-out", "falling_late": "the last of the run-out",
}


# ------------------------------------------------------------------ evidence

def report_evidence(obs: list[dict], loc_id: str, species_id: str, on: datetime, rules: dict) -> tuple[float, list[dict]]:
    """Decayed evidence score (0–1) and the supporting observations."""
    hl = rules["reports"]["half_life_days"]
    max_age = rules["reports"]["max_age_days"]
    pw = rules["reports"]["provenance_weight"]
    total, ev = 0.0, []
    for o in obs:
        if species_id not in o.get("species", []):
            continue
        if loc_id not in o.get("locations", []):
            continue
        d = o.get("catch_date") or o.get("report_date")
        try:
            age = (on.date() - datetime.strptime(d, "%Y-%m-%d").date()).days
        except (TypeError, ValueError):
            continue
        if age < -1 or age > max_age:
            continue
        w = pw.get(o.get("provenance", "automated"), 1.0) * (0.5 ** (max(age, 0) / hl))
        if o.get("rating") is not None:
            w *= (o["rating"] - 1) / 4  # 1→0, 5→1
        total += w
        ev.append({"source": o.get("source_name"), "credit": o.get("credit"), "date": o.get("report_date"),
                   "catch_date": o.get("catch_date"), "url": o.get("url"), "provenance": o.get("provenance"),
                   "age_days": age, "weight": round(w, 2), "excerpt": _excerpt(o.get("text", ""), species_id)})
    ev.sort(key=lambda e: -e["weight"])
    return min(1.0, 1 - math.exp(-total)), ev[:4]


def _excerpt(text: str, species_id: str) -> str:
    from .ingest.extract import SPECIES_TERMS, sentences_mentioning
    s = sentences_mentioning(text, SPECIES_TERMS.get(species_id, [species_id]))
    return (s[0] if s else text[:160])[:220]


# ------------------------------------------------------------------ gate

def gate(loc: dict, species: dict, day: datetime, ctx: dict) -> dict:
    """Return {'status': ok|excluded|capped, 'cap': int|None, 'colour': ..., 'reasons': [...]}."""
    rules = ctx["rules"]
    reasons, cap, colour, status = [], None, None, "ok"
    zone = rules["zones"].get(loc.get("zone"), {})
    if zone.get("fishing") == "prohibited":
        return {"status": "excluded", "reasons": [f"{zone['name']} — no fishing"], "cap": None, "colour": "grey"}
    for cid in species.get("legal", {}).get("closures", []):
        c = next((x for x in rules["closures"] if x["id"] == cid), None)
        if c and closure_active(c, day):
            return {"status": "excluded", "reasons": [f"{c['name']} in force"], "cap": None, "colour": "grey"}
    for a in ctx.get("alerts", []):
        if loc["id"] in a.get("locations", []) and a.get("severity") == "closure":
            status, cap, colour = "capped", 20, "red"
            reasons.append(f"QPWS alert: {a['title']}")
    if ctx.get("marine_warning"):
        mc = rules["safety"]["marine_warning_caps"].get(loc["type"])
        if mc:
            status, cap, colour = "capped", min(cap or 100, mc["cap"]), mc["colour"] if colour != "red" else "red"
            reasons.append("BOM marine warning current for this coast")
    return {"status": status, "cap": cap, "colour": colour, "reasons": reasons}


def closure_active(c: dict, day: datetime) -> bool:
    md = day.strftime("%m-%d")
    spans = c.get("annual_multi") or ([c["annual"]] if c.get("annual") else [])
    for s in spans:
        if s["start"] <= s["end"]:
            if s["start"] <= md <= s["end"]:
                return True
        elif md >= s["start"] or md <= s["end"]:   # wraps year end
            return True
    return False


# ------------------------------------------------------------------ windows

def candidate_windows(day: datetime, astro: dict, hilo: list[dict]) -> list[tuple[datetime, datetime, str]]:
    """2.5 h windows around dawn, dusk and each tide turn; merged when overlapping."""
    wins = []
    sr, ss = datetime.fromisoformat(astro["sunrise"]), datetime.fromisoformat(astro["sunset"])
    wins.append((sr - timedelta(minutes=60), sr + timedelta(minutes=90), "dawn"))
    wins.append((ss - timedelta(minutes=90), ss + timedelta(minutes=60), "dusk"))
    d0, d1 = day, day + timedelta(days=1)
    for r in hilo:
        t = datetime.fromisoformat(r["t"])
        if d0 <= t < d1:
            wins.append((t - timedelta(minutes=90), t + timedelta(minutes=60), f"{'high' if r['type']=='H' else 'low'} tide {t.strftime('%H:%M')}"))
    wins.sort()
    merged: list[list] = []
    for s, e, lab in wins:
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
            merged[-1][2] += " + " + lab
        else:
            merged.append([s, e, lab])
    out = []
    for s, e, lab in merged:
        s = max(s, d0); e = min(e, d1 - timedelta(minutes=1))
        if (e - s) >= timedelta(minutes=60):
            out.append((s, e, lab))
    return out


def _hour_key(t: datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:00")


def _avg(vals):
    v = [x for x in vals if x is not None]
    return sum(v) / len(v) if v else None


# ------------------------------------------------------------------ score one combination

def score_window(loc: dict, species: dict, win: tuple, day: datetime, ctx: dict) -> dict | None:
    s, e, label = win
    wx = ctx["weather"].get(loc["id"])
    mar = ctx["marine"].get(loc.get("marine_point", "ocean"))
    hilo = ctx["tides"].get(loc["tide_ref"], [])
    astro = ctx["astro"][day.strftime("%Y-%m-%d")]
    if not wx or not wx.get("time"):
        return None
    hours = []
    t = s.replace(minute=0)
    while t <= e:
        hours.append(t); t += timedelta(hours=1)
    mid = s + (e - s) / 2
    keys = [_hour_key(h) for h in hours]
    wind_kn = _avg([at(wx, "wind_speed_10m", k) for k in keys])
    gust_kn = _avg([at(wx, "wind_gusts_10m", k) for k in keys])
    wind_dir = at(wx, "wind_direction_10m", _hour_key(mid)) or _avg([at(wx, "wind_direction_10m", k) for k in keys])
    hs = _avg([at(mar, "wave_height", k) for k in keys]) if mar else None
    swell_h = _avg([at(mar, "swell_wave_height", k) for k in keys]) if mar else None
    swell_p = _avg([at(mar, "swell_wave_period", k) for k in keys]) if mar else None
    sst = _avg([at(mar, "sea_surface_temperature", k) for k in keys]) if mar else None
    rain24 = _rain(wx, mid, 24); rain72 = _rain(wx, mid, 72)
    if wind_kn is None:
        return None
    stage = model.tide_stage(mid, hilo)
    exp = model.wind_exposure(wind_dir, wind_kn, loc)
    period = light_period(mid, astro)
    rules = ctx["rules"]

    f = {
        "tide": model.tide_factor(stage, species.get("tide_pref", [])),
        "wind": model.wind_factor(exp, species, loc["type"]),
        "swell": model.swell_factor(hs, swell_p, species, loc["type"]),
        "light": model.light_factor(period, species),
        "season": model.season_factor(day.month, species),
        "pressure": model.pressure_factor(ctx.get("pressure_trend")),
        "rain": model.rain_factor(rain24, rain72, species, loc["type"]),
        "lunar": model.lunar_factor(astro),
    }
    rep, evidence = report_evidence(ctx["observations"], loc["id"], species["id"], day, rules)
    f["reports"] = round(0.35 + 0.65 * rep, 2)   # no reports ≠ bad; it's just unknown
    w = WEIGHTS[loc["type"]]
    raw = sum(w[k] * f[k] for k in w)
    score = round(100 * raw)

    g = gate(loc, species, day, ctx)
    warnings = list(g["reasons"])
    colour = None
    if g["status"] == "excluded":
        return None
    # hard environmental limits
    lim = rules["safety"]
    if wind_kn >= lim["wind_hard_limits_kn"].get(loc["type"], 30):
        score = min(score, 30); colour = "red"; warnings.append(f"Sustained wind ~{round(wind_kn)} kn — impractical")
    shl = lim["swell_hard_limits"].get(loc["type"])
    if shl and hs is not None and hs > shl["cap_above_m"]:
        score = min(score, shl["cap"]); colour = "red"; warnings.append(f"Seas ~{hs:.1f} m — dangerous surf")
    if g["cap"] is not None:
        score = min(score, g["cap"]); colour = g["colour"]
    # 4WD access tide rule
    acc = loc.get("access", {})
    if acc.get("vehicle") == "4wd" and stage and "high" in (acc.get("tide_window") or "") and stage["stage"] in ("rising_late", "high_turn", "falling_early") and loc["type"] == "surf_beach":
        score = min(score, lim["access_tide_cap"]["cap"]); colour = colour or lim["access_tide_cap"]["colour"]
        warnings.append("Window sits around high tide — beach driving access restricted")

    # confidence
    stale = ctx["health"].get("stale_categories", [])
    horizon = (day.date() - ctx["today"].date()).days
    conf = "high" if (evidence and not stale) else "medium"
    if stale:
        conf = "low"
    if horizon >= 3:
        conf = {"high": "medium", "medium": "low", "low": "low"}[conf]
    if horizon >= 5:
        conf = "low"
    if stage and stage.get("modelled"):
        conf = {"high": "medium", "medium": "low", "low": "low"}[conf]

    if colour is None:
        colour = "green" if score >= 65 else "amber" if score >= 45 else "red"

    basis = ["conditions", "season"] + (["reports"] if evidence else [])
    return {
        "location": loc["id"], "species": species["id"],
        "window": {"start": s.strftime("%H:%M"), "end": e.strftime("%H:%M"), "label": label,
                   "start_iso": s.isoformat(timespec="minutes"), "end_iso": e.isoformat(timespec="minutes")},
        "score": int(score), "colour": colour, "confidence": conf, "basis": basis,
        "factors": f, "warnings": warnings,
        "conditions": {
            "wind_kn": round(wind_kn), "gust_kn": round(gust_kn) if gust_kn else None,
            "wind_dir": exp.get("compass"), "wind_relation": exp.get("relation"), "effective_wind_kn": exp.get("effective_kn"),
            "seas_m": round(hs, 1) if hs is not None else None, "swell_m": round(swell_h, 1) if swell_h is not None else None,
            "swell_period_s": round(swell_p) if swell_p else None, "sst_c": round(sst, 1) if sst else None,
            "tide_stage": stage["stage"] if stage else None, "tide_range_m": stage["range_m"] if stage else None,
            "tide_next": stage["next"] if stage else None, "light": period, "rain_24h_mm": round(rain24 or 0, 1),
        },
        "evidence": evidence,
        "explain": explain(loc, species, f, exp, stage, period, evidence, warnings, hs, wind_kn),
    }


def _rain(wx: dict, t: datetime, hours: int) -> float | None:
    vals = []
    for h in range(hours):
        v = at(wx, "precipitation", _hour_key(t - timedelta(hours=h)))
        if v is not None:
            vals.append(v)
    return sum(vals) if vals else None


# ------------------------------------------------------------------ explanation

def explain(loc, species, f, exp, stage, period, evidence, warnings, hs, wind_kn) -> str:
    parts = []
    rel = exp.get("relation")
    comp = exp.get("compass") or ""
    if rel == "offshore":
        parts.append(f"{comp} wind at ~{round(wind_kn)} kn is offshore for this {'shore' if loc['type']!='surf_beach' else 'beach'}")
    elif rel == "cross":
        parts.append(f"{comp} wind at ~{round(wind_kn)} kn is across the beach")
    elif rel == "onshore":
        parts.append(f"{comp} wind at ~{round(wind_kn)} kn is onshore" + (" but the spot is well sheltered" if exp.get("shelter", 1) < 0.5 else ""))
    if stage:
        word = STAGE_WORDS.get(stage["stage"], stage["stage"])
        liked = stage["stage"] in species.get("tide_pref", [])
        parts.append(f"the window covers {word}" + (f", which suits {species['name'].lower()}" if liked else ""))
    if period in species.get("light_pref", []):
        parts.append(f"{period} is a preferred time for this species")
    if loc["type"] in ("surf_beach", "headland") and hs is not None:
        parts.append(f"seas around {hs:.1f} m")
    if f["season"] >= 1.0:
        parts.append(f"{species['name'].lower()} are in peak season")
    elif f["season"] <= 0.2:
        parts.append(f"{species['name'].lower()} are out of season")
    if evidence:
        e = evidence[0]
        who = e.get("credit") or e.get("source")
        n = len(evidence)
        parts.append(f"{n} recent report{'s' if n > 1 else ''} mention{'' if n > 1 else 's'} {species['name'].lower()} nearby (latest {who}, {e['date']})")
    else:
        parts.append("no recent public reports for this species here — ranking rests on conditions and seasonal patterns")
    text = "; ".join(parts)
    text = text[0].upper() + text[1:] + "."
    if warnings:
        text += " ⚠ " + " ".join(warnings)
    return text


# ------------------------------------------------------------------ day

def score_day(day: datetime, ctx: dict) -> dict:
    cfg = ctx["config"]
    locs = cfg["locations"]["locations"]
    species = {s["id"]: s for s in cfg["species"]["species"]}
    astro = ctx["astro"][day.strftime("%Y-%m-%d")]
    opportunities = []
    per_loc: dict[str, dict] = {}
    for loc in locs:
        hilo = ctx["tides"].get(loc["tide_ref"], [])
        wins = candidate_windows(day, astro, hilo)
        best_for_loc = []
        for sid in loc["species"]:
            sp = species.get(sid)
            if not sp:
                continue
            for w in wins:
                r = score_window(loc, sp, w, day, ctx)
                if r:
                    opportunities.append(r)
                    best_for_loc.append(r)
        best_for_loc.sort(key=lambda r: -r["score"])
        if best_for_loc:
            top = best_for_loc[0]
            seen, best_species = set(), []
            for r in best_for_loc:
                if r["species"] not in seen:
                    seen.add(r["species"]); best_species.append({"species": r["species"], "score": r["score"], "window": r["window"]})
                if len(best_species) >= 3:
                    break
            per_loc[loc["id"]] = {
                "score": top["score"], "colour": top["colour"], "confidence": top["confidence"],
                "best_species": best_species, "best_window": top["window"], "conditions": top["conditions"],
                "warnings": sorted(set(w for r in best_for_loc[:5] for w in r["warnings"])),
                "explain": top["explain"], "evidence": top["evidence"],
            }
        else:
            per_loc[loc["id"]] = {"score": None, "colour": "grey", "confidence": "none", "best_species": [],
                                  "warnings": ["Insufficient data"], "explain": "No forecast data available for this location today."}
    opportunities.sort(key=lambda r: (-r["score"], r["window"]["start"]))
    # diversify top list: max 2 per location in top 10
    top, count = [], {}
    for r in opportunities:
        if count.get(r["location"], 0) >= 2:
            continue
        top.append(r); count[r["location"]] = count.get(r["location"], 0) + 1
        if len(top) >= 10:
            break
    for i, r in enumerate(top, 1):
        r["rank"] = i
    return {"date": day.strftime("%Y-%m-%d"), "astro": astro, "top": top,
            "locations": per_loc, "all_count": len(opportunities)}
