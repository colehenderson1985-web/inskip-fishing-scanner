"""Environmental interpretation: tide stage, wind exposure, swell bands, season."""
from __future__ import annotations

import math
from datetime import datetime, timedelta

COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
COMPASS8_DEG = {"N": 0, "NE": 45, "E": 90, "SE": 135, "S": 180, "SW": 225, "W": 270, "NW": 315}


def deg_to_compass(deg: float | None) -> str | None:
    if deg is None:
        return None
    return COMPASS[int((deg / 22.5) + 0.5) % 16]


def angle_diff(a: float, b: float) -> float:
    d = abs(a - b) % 360
    return d if d <= 180 else 360 - d


# ------------------------------------------------------------------ tide

def _aware(s: str) -> datetime:
    from zoneinfo import ZoneInfo
    d = datetime.fromisoformat(s)
    return d if d.tzinfo else d.replace(tzinfo=ZoneInfo("Australia/Brisbane"))


def tide_stage(t: datetime, hilo: list[dict]) -> dict | None:
    """Classify t relative to surrounding high/low: stage name, minutes to next turn, range."""
    prev = nxt = None
    ts = t.isoformat(timespec="minutes")
    for r in hilo:
        if r["t"] <= ts:
            prev = r
        elif nxt is None:
            nxt = r
            break
    if not prev or not nxt:
        return None
    pt = _aware(prev["t"]); nt = _aware(nxt["t"])
    total = (nt - pt).total_seconds() / 60
    elapsed = (t - pt).total_seconds() / 60
    frac = elapsed / total if total else 0
    rising = nxt["type"] == "H"
    rng = abs(nxt["h"] - prev["h"])
    if frac < 0.17:
        stage = "low_turn" if rising else "high_turn"
    elif frac > 0.83:
        stage = "high_turn" if rising else "low_turn"
    elif frac < 0.5:
        stage = "rising_early" if rising else "falling_early"
    else:
        stage = "rising_late" if rising else "falling_late"
    return {
        "stage": stage, "rising": rising, "range_m": round(rng, 2),
        "prev": prev, "next": nxt,
        "min_to_next": round(total - elapsed), "min_from_prev": round(elapsed),
        "modelled": bool(prev.get("modelled") or nxt.get("modelled")),
    }


def tide_prefs_for(species: dict, loc_type: str) -> list[str]:
    tp = species.get("tide_pref", [])
    if isinstance(tp, dict):
        return tp.get(loc_type) or tp.get("default") or []
    return tp


def tide_factor(stage: dict | None, prefs: list[str]) -> float:
    if not stage:
        return 0.5
    s = stage["stage"]
    adjacent = {
        "low_turn": ["rising_early", "falling_late"], "rising_early": ["low_turn", "rising_late"],
        "rising_late": ["rising_early", "high_turn"], "high_turn": ["rising_late", "falling_early"],
        "falling_early": ["high_turn", "falling_late"], "falling_late": ["falling_early", "low_turn"],
    }
    if s in prefs:
        base = 1.0
    elif any(a in prefs for a in adjacent[s]):
        base = 0.55
    else:
        base = 0.2
    # bigger range → stronger flow; mild effect
    rng_bonus = min(stage["range_m"], 2.0) / 2.0 * 0.1
    return round(min(1.0, base * 0.9 + rng_bonus), 2)


# ------------------------------------------------------------------ wind

def wind_exposure(wind_from_deg: float | None, wind_kn: float | None, loc: dict) -> dict:
    """Effective wind at the location: relation to shore aspect and shelter."""
    if wind_from_deg is None or wind_kn is None:
        return {"relation": None, "effective_kn": None, "factor": 0.5}
    aspect = loc["aspect_deg"]
    # wind FROM aspect = blowing from the water onto the shore = onshore
    d = angle_diff(wind_from_deg, aspect)
    if d <= 45:
        relation = "onshore"
    elif d <= 110:
        relation = "cross"
    else:
        relation = "offshore"
    shelter = 1.0
    comp = deg_to_compass(wind_from_deg)
    if comp:
        comp8 = _to8(wind_from_deg)
        if comp8 in loc.get("shelter_from", []):
            shelter = 1.0 - loc.get("shelter_degree", 0.5)
    eff = wind_kn * (shelter if relation != "onshore" else 1.0)
    return {"relation": relation, "effective_kn": round(eff, 1), "shelter": shelter, "compass": comp}


def _to8(deg: float) -> str:
    return ["N", "NE", "E", "SE", "S", "SW", "W", "NW"][int((deg / 45) + 0.5) % 8]


def wind_factor(exp: dict, species: dict, loc_type: str) -> float:
    if exp["effective_kn"] is None:
        return 0.5
    kn = exp["effective_kn"]
    rel = exp["relation"]
    max_on = species.get("wind", {}).get("max_onshore_kn", 20)
    if rel == "offshore":
        f = 1.0 if kn <= 12 else max(0.35, 1.0 - (kn - 12) / 22)
        if species.get("wind", {}).get("offshore_bonus") and kn <= 15:
            f = min(1.0, f + 0.05)
    elif rel == "cross":
        f = 0.8 if kn <= 10 else max(0.25, 0.8 - (kn - 10) / 20)
    else:  # onshore — hurts quickly on open beaches
        if kn <= 6:
            f = 0.7
        elif kn <= max_on * 0.6:
            f = 0.55
        elif kn <= max_on:
            f = 0.35
        else:
            f = max(0.08, 0.35 - (kn - max_on) / 15)
    if loc_type in ("estuary", "sheltered_strait"):
        f = 0.45 + 0.55 * f   # wind matters less inside, but still matters
    return round(f, 2)


# ------------------------------------------------------------------ swell

def swell_factor(hs: float | None, period: float | None, species: dict, loc_type: str) -> float:
    if loc_type in ("estuary", "sheltered_strait"):
        return 0.8 if hs is None or hs < 2.5 else 0.6
    if hs is None:
        return 0.5
    sw = species.get("swell", {})
    lo, hi = sw.get("ideal", [0.5, 1.5])
    mn, mx = sw.get("min_m", 0.0), sw.get("max_m", 2.5)
    if lo <= hs <= hi:
        f = 1.0
    elif mn <= hs < lo:
        f = 0.55 + 0.45 * (hs - mn) / max(lo - mn, 0.01)
    elif hi < hs <= mx:
        f = 1.0 - 0.65 * (hs - hi) / max(mx - hi, 0.01)
    else:
        f = 0.2 if hs > mx else 0.45
    if period and period >= 10 and loc_type == "surf_beach":
        f = min(1.0, f + 0.05)
    return round(max(0.1, f), 2)


# ------------------------------------------------------------------ season / light / lunar / pressure / rain

def season_factor(month: int, species: dict) -> float:
    s = species.get("season", {})
    if month in s.get("peak", []):
        return 1.0
    if month in s.get("shoulder", []):
        return 0.5
    return 0.15


def light_factor(period: str, species: dict) -> float:
    prefs = species.get("light_pref", ["day"])
    if period in prefs:
        return 1.0
    if period in ("dawn", "dusk") and "day" in prefs:
        return 0.8
    if period == "night" and ("dusk" in prefs or "dawn" in prefs):
        return 0.55
    return 0.3


def lunar_factor(astro: dict) -> float:
    return 0.7 if astro.get("near_new_or_full") else 0.5


def pressure_factor(trend: str | None) -> float:
    return {"rising": 0.8, "steady": 0.75, "falling": 0.6, "falling_fast": 0.45}.get(trend or "", 0.65)


def rain_factor(rain_24h_mm: float | None, rain_72h_mm: float | None, species: dict, loc_type: str) -> float:
    r24 = rain_24h_mm or 0.0
    r72 = rain_72h_mm or 0.0
    clarity = species.get("clarity", "any")
    if loc_type in ("estuary", "sheltered_strait"):
        if 5 <= r72 <= 40:
            return 0.85   # a flush brings bait and predators
        if r72 > 80:
            return 0.4 if clarity != "any" else 0.6
        return 0.7
    if clarity == "clear" and r24 > 25:
        return 0.45
    return 0.7


def sst_factor(sst_c: float | None, species: dict) -> float | None:
    """Warm-water species (jacks, mackerel, cobia) switch on above a threshold. None = not applicable."""
    cfg = species.get("sst")
    if not cfg or sst_c is None:
        return None
    mn, ideal = cfg.get("min_c", 21), cfg.get("ideal_c", 24)
    if sst_c >= ideal:
        return 1.0
    if sst_c <= mn - 2:
        return 0.25
    return round(0.25 + 0.75 * (sst_c - (mn - 2)) / max(ideal - (mn - 2), 0.1), 2)
