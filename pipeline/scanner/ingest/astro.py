"""Sun and moon — computed locally with astral (no network)."""
from __future__ import annotations

import math
from datetime import datetime, timedelta

from astral import LocationInfo, moon
from astral.sun import sun

from ..util import TZ, iso
from . import solunar


def day_astro(date: datetime, lat: float, lon: float) -> dict:
    li = LocationInfo("site", "AU", "Australia/Brisbane", lat, lon)
    s = sun(li.observer, date=date.date(), tzinfo=TZ)
    phase_days = moon.phase(date.date())            # 0 = new, ~14.77 = full, period ~29.53
    frac = phase_days / 29.53
    illum = 0.5 * (1 - math.cos(2 * math.pi * frac))
    name = _phase_name(phase_days)
    try:
        mr = moon.moonrise(li.observer, date.date(), tzinfo=TZ)
    except Exception:  # noqa: BLE001
        mr = None
    try:
        ms = moon.moonset(li.observer, date.date(), tzinfo=TZ)
    except Exception:  # noqa: BLE001
        ms = None
    near_new_full = min(phase_days, abs(phase_days - 14.77), abs(phase_days - 29.53)) <= 3.0
    sol = solunar.day_solunar(date, lat, lon, iso(mr), iso(ms))
    return {
        "date": date.strftime("%Y-%m-%d"),
        "dawn": iso(s["dawn"]), "sunrise": iso(s["sunrise"]),
        "sunset": iso(s["sunset"]), "dusk": iso(s["dusk"]),
        "moonrise": iso(mr), "moonset": iso(ms),
        "moon_phase_days": round(phase_days, 1), "moon_illumination": round(illum, 2),
        "moon_phase": name, "near_new_or_full": near_new_full,
        "solunar": sol,
    }


def _phase_name(d: float) -> str:
    if d < 1.85 or d >= 27.7:
        return "New moon"
    if d < 5.5:
        return "Waxing crescent"
    if d < 9.2:
        return "First quarter"
    if d < 12.9:
        return "Waxing gibbous"
    if d < 16.6:
        return "Full moon"
    if d < 20.3:
        return "Waning gibbous"
    if d < 24.0:
        return "Last quarter"
    return "Waning crescent"


def light_period(t: datetime, a: dict) -> str:
    """Classify a time as dawn / day / dusk / night using civil twilight ±."""
    sr = datetime.fromisoformat(a["sunrise"])
    ss = datetime.fromisoformat(a["sunset"])
    if sr - timedelta(minutes=75) <= t <= sr + timedelta(minutes=75):
        return "dawn"
    if ss - timedelta(minutes=75) <= t <= ss + timedelta(minutes=75):
        return "dusk"
    if sr < t < ss:
        return "day"
    return "night"
