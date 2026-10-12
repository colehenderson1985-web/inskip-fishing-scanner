"""Almanac-style lunar rating and solunar bite times — computed locally, no network.

This reproduces the *kind* of guidance printed in Australian angler's almanacs (best/good/fair/poor days
from the moon's phase, plus major/minor "bite times" from the moon's position). It is our own computation,
not a copy of any published almanac's tables, and is labelled that way on the dashboard.

Solunar theory has weak scientific support. The scanner treats it as a modest-weight hypothesis that the
group's session ratings can confirm or reject.

- Major periods: ~2 h centred on lunar upper transit (moon overhead) and lower transit (moon underfoot).
- Minor periods: ~1 h centred on moonrise and moonset.
- Day rating: from distance to new / full moon, with quarter phases treated as fair, nudged up one step
  near perigee (moon closest, bigger tides) and down one step near apogee.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from astral import Observer, moon

from ..util import TZ

SYNODIC = 29.530589
RATINGS = ["Poor", "Fair", "Good", "Best"]
RATING_FACTOR = {"Best": 0.9, "Good": 0.75, "Fair": 0.55, "Poor": 0.4}
MAJOR_HALF = timedelta(minutes=60)
MINOR_HALF = timedelta(minutes=30)
PERIGEE_KM = 366_000
APOGEE_KM = 402_000


# ------------------------------------------------------------------ moon distance (Meeus, low precision)

def moon_distance_km(t: datetime) -> float:
    """Geocentric Earth–Moon distance, accurate to a few hundred km — plenty to flag perigee/apogee."""
    tu = t.astimezone(TZ).timestamp() / 86400.0 + 2440587.5      # Julian day
    T = (tu - 2451545.0) / 36525.0
    D = math.radians((297.8501921 + 445267.1114034 * T) % 360)
    M = math.radians((357.5291092 + 35999.0502909 * T) % 360)
    Mp = math.radians((134.9633964 + 477198.8675055 * T) % 360)
    return (385000.56
            - 20905.355 * math.cos(Mp)
            - 3699.111 * math.cos(2 * D - Mp)
            - 2955.968 * math.cos(2 * D)
            - 569.925 * math.cos(2 * Mp)
            + 48.888 * math.cos(M)
            + 246.158 * math.cos(2 * D - 2 * Mp)
            - 152.138 * math.cos(2 * D - M - Mp)
            - 170.733 * math.cos(2 * D + Mp)
            - 204.586 * math.cos(2 * D - M)
            - 129.620 * math.cos(Mp - M)
            + 108.743 * math.cos(D)
            + 104.755 * math.cos(Mp + M))


# ------------------------------------------------------------------ transits

def _elev(obs: Observer, t: datetime) -> float:
    # astral's moon.elevation reads the wall-clock fields as UTC, so convert first
    return moon.elevation(obs, t.astimezone(timezone.utc))


def transits(day: datetime, lat: float, lon: float) -> list[dict]:
    """Upper (overhead) and lower (underfoot) lunar transits during the local calendar day."""
    obs = Observer(latitude=lat, longitude=lon)
    d0 = datetime(day.year, day.month, day.day, tzinfo=TZ)
    step = timedelta(minutes=10)
    pts = []
    t = d0 - step
    while t <= d0 + timedelta(days=1) + step:
        pts.append((t, _elev(obs, t)))
        t += step
    out = []
    for i in range(1, len(pts) - 1):
        (_, a), (tb, b), (_, c) = pts[i - 1], pts[i], pts[i + 1]
        kind = "overhead" if (b >= a and b > c) else "underfoot" if (b <= a and b < c) else None
        if not kind:
            continue
        # parabolic refinement of the extremum between neighbours
        denom = a - 2 * b + c
        off = 0.5 * (a - c) / denom if denom else 0.0
        tt = tb + step * off
        if d0 <= tt < d0 + timedelta(days=1):
            out.append({"kind": kind, "t": tt.replace(second=0, microsecond=0)})
    return out


# ------------------------------------------------------------------ day rating

def phase_days(day: datetime) -> float:
    return moon.phase(day.date())   # astral: 0 = new, ~14.77 = full, period ~29.53


def day_rating(day: datetime) -> dict:
    p = phase_days(day)
    half = SYNODIC / 2
    to_syzygy = min(p % half, half - (p % half))        # days from nearest new or full moon
    to_quarter = abs((p % half) - half / 2)             # days from nearest quarter
    if to_syzygy <= 1.5:
        base = "Best"
    elif to_syzygy <= 3.5:
        base = "Good"
    elif to_quarter <= 1.5:
        base = "Fair"
    else:
        base = "Poor"
    noon = datetime(day.year, day.month, day.day, 12, tzinfo=TZ)
    dist = moon_distance_km(noon)
    idx = RATINGS.index(base)
    nudge = None
    if dist < PERIGEE_KM:
        idx = min(idx + 1, 3); nudge = "perigee"
    elif dist > APOGEE_KM:
        idx = max(idx - 1, 0); nudge = "apogee"
    rating = RATINGS[idx]
    return {"rating": rating, "base_rating": base, "factor": RATING_FACTOR[rating],
            "days_from_new_or_full": round(to_syzygy, 1), "moon_distance_km": int(round(dist, -2)),
            "distance_note": nudge}


# ------------------------------------------------------------------ assemble

def _period(centre: datetime, half: timedelta, kind: str) -> dict:
    return {"kind": kind, "centre": centre.isoformat(timespec="minutes"),
            "start": (centre - half).isoformat(timespec="minutes"),
            "end": (centre + half).isoformat(timespec="minutes")}


def day_solunar(day: datetime, lat: float, lon: float, moonrise: str | None, moonset: str | None) -> dict:
    r = day_rating(day)
    majors = [_period(x["t"], MAJOR_HALF, x["kind"]) for x in transits(day, lat, lon)]
    minors = []
    for t, kind in ((moonrise, "moonrise"), (moonset, "moonset")):
        if t:
            minors.append(_period(datetime.fromisoformat(t), MINOR_HALF, kind))
    minors.sort(key=lambda m: m["centre"])
    return {**r, "majors": majors, "minors": minors,
            "label": "Almanac-style lunar rating (computed, not the published Almanac)"}


def overlap(start: datetime, end: datetime, sol: dict | None) -> dict:
    """Which solunar periods a fishing window overlaps."""
    if not sol:
        return {"major": None, "minor": None}
    def hit(periods):
        for p in periods:
            ps, pe = datetime.fromisoformat(p["start"]), datetime.fromisoformat(p["end"])
            if ps < end and pe > start:
                return p
        return None
    return {"major": hit(sol.get("majors", [])), "minor": hit(sol.get("minors", []))}


def lunar_factor(sol: dict | None, ov: dict) -> float:
    """Day rating (60 %) blended with whether the window overlaps a bite time (40 %)."""
    if not sol:
        return 0.5
    bite = 1.0 if ov.get("major") else 0.75 if ov.get("minor") else 0.45
    return round(0.6 * sol["factor"] + 0.4 * bite, 2)
