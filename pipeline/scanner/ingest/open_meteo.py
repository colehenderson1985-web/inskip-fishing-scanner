"""Open-Meteo forecast + marine ingestion.

Returns hourly series in AEST for each location point and marine point.
Free, no key, CC BY 4.0. https://open-meteo.com
"""
from __future__ import annotations

from ..util import StepResult, archive_raw, get, log, now, write_json, CACHE, read_json

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"

HOURLY_WX = [
    "temperature_2m", "precipitation", "pressure_msl",
    "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m", "cloud_cover",
]
HOURLY_MARINE = [
    "wave_height", "wave_direction", "wave_period",
    "swell_wave_height", "swell_wave_direction", "swell_wave_period",
    "wind_wave_height", "sea_surface_temperature", "sea_level_height_msl",
]


def _fetch(url: str, params: dict, name: str) -> dict:
    r = get(url, params=params, timeout=40)
    archive_raw("open_meteo", f"{name}.json", r.content)
    return r.json()


def fetch_weather(locations: list[dict], days: int = 10) -> tuple[dict, StepResult]:
    """One call per distinct location centre (rounded to 2 dp to share cells)."""
    out: dict[str, dict] = {}
    try:
        seen: dict[tuple, dict] = {}
        for loc in locations:
            lat, lon = round(loc["centre"][0], 2), round(loc["centre"][1], 2)
            key = (lat, lon)
            if key not in seen:
                params = {
                    "latitude": lat, "longitude": lon,
                    "hourly": ",".join(HOURLY_WX),
                    "daily": "sunrise,sunset,precipitation_sum",
                    "wind_speed_unit": "kn",
                    "timezone": "Australia/Brisbane",
                    "forecast_days": days, "past_days": 1,
                }
                seen[key] = _fetch(FORECAST_URL, params, f"forecast_{lat}_{lon}")
            out[loc["id"]] = _series(seen[key])
        write_json(CACHE / "weather.json", out)
        return out, StepResult("open_meteo_forecast", True, items=len(out))
    except Exception as e:  # noqa: BLE001
        log.exception("open-meteo forecast failed")
        cached = read_json(CACHE / "weather.json", {})
        return cached, StepResult("open_meteo_forecast", False, items=len(cached), error=str(e))


def fetch_marine(points: dict[str, dict], days: int = 8) -> tuple[dict, StepResult]:
    out: dict[str, dict] = {}
    try:
        for pid, p in points.items():
            params = {
                "latitude": p["lat"], "longitude": p["lon"],
                "hourly": ",".join(HOURLY_MARINE),
                "timezone": "Australia/Brisbane",
                "forecast_days": days, "past_days": 1,
                "cell_selection": "sea",
            }
            out[pid] = _series(_fetch(MARINE_URL, params, f"marine_{pid}"))
            out[pid]["name"] = p.get("name", pid)
        write_json(CACHE / "marine.json", out)
        return out, StepResult("open_meteo_marine", True, items=len(out))
    except Exception as e:  # noqa: BLE001
        log.exception("open-meteo marine failed")
        cached = read_json(CACHE / "marine.json", {})
        return cached, StepResult("open_meteo_marine", False, items=len(cached), error=str(e))


def _series(j: dict) -> dict:
    """Normalise to {'time': [...], var: [...], 'units': {...}, 'daily': {...}}."""
    h = j.get("hourly", {})
    s = {"time": h.get("time", []), "units": j.get("hourly_units", {}),
         "lat": j.get("latitude"), "lon": j.get("longitude"),
         "model": j.get("model") or "best_match", "fetched_at": now().isoformat(timespec="seconds")}
    for k, v in h.items():
        if k != "time":
            s[k] = v
    if "daily" in j:
        s["daily"] = j["daily"]
    return s


def at(series: dict, var: str, t: str):
    """Value of var at ISO hour string t (YYYY-MM-DDTHH:00); None if absent."""
    try:
        i = series["time"].index(t)
        return series.get(var, [None] * len(series["time"]))[i]
    except (ValueError, KeyError):
        return None
