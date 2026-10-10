"""Generate clearly-labelled synthetic cached data so the pipeline can run
offline (tests, local dev, and before the first live fetch). Never used in
production runs: the refresh job fetches real data and overwrites the cache.
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scanner.util import CACHE, TZ, load_yaml, write_json, OBS  # noqa: E402


def hourly(start: datetime, hours: int):
    return [(start + timedelta(hours=i)) for i in range(hours)]


def make(seed_day: datetime | None = None, label: str = "SYNTHETIC DEMO DATA"):
    cfg = load_yaml("locations.yaml")
    t0 = (seed_day or datetime.now(TZ)).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    hrs = hourly(t0, 24 * 11)
    times = [h.strftime("%Y-%m-%dT%H:%M") for h in hrs]
    weather = {}
    for loc in cfg["locations"]:
        ws, wd, wg, p, pr, tt = [], [], [], [], [], []
        for i, h in enumerate(hrs):
            day = i // 24
            # SW offshore mornings swinging NE afternoons, strengthening mid-week
            base_dir = 220 if h.hour < 11 else 50
            ws.append(round(6 + 4 * math.sin(i / 7) + day * 1.5 + (6 if h.hour > 12 else 0), 1))
            wd.append(base_dir + (day * 10) % 60)
            wg.append(round(ws[-1] * 1.4, 1))
            p.append(round(1018 - day * 1.2 + 1.5 * math.sin(i / 12), 1))
            pr.append(0.0 if day not in (3, 4) else 1.2)
            tt.append(round(19 + 6 * math.sin((h.hour - 8) / 24 * 2 * math.pi), 1))
        weather[loc["id"]] = {"time": times, "wind_speed_10m": ws, "wind_direction_10m": wd, "wind_gusts_10m": wg,
                              "pressure_msl": p, "precipitation": pr, "temperature_2m": tt,
                              "units": {"wind_speed_10m": "kn"}, "lat": loc["centre"][0], "lon": loc["centre"][1],
                              "model": label, "fetched_at": datetime.now(TZ).isoformat(timespec="seconds")}
    marine = {}
    for pid, pt in cfg["region"]["marine_points"].items():
        hs = [round(1.0 + 0.5 * math.sin(i / 30) + (0.3 if pid == "bar" else 0), 2) for i in range(len(hrs))]
        marine[pid] = {"time": times, "wave_height": hs, "swell_wave_height": [round(x * 0.8, 2) for x in hs],
                       "swell_wave_direction": [110] * len(hrs), "swell_wave_period": [round(9 + 2 * math.sin(i / 40), 1) for i in range(len(hrs))],
                       "sea_surface_temperature": [round(22.5 + 0.3 * math.sin(i / 50), 1) for i in range(len(hrs))],
                       "sea_level_height_msl": [round(0.9 * math.sin(2 * math.pi * i / 12.42), 2) for i in range(len(hrs))],
                       "name": pt["name"], "lat": pt["lat"], "lon": pt["lon"], "model": label}
    # tides: semidiurnal, ~12h25m, offset per station
    year = t0.year
    for sid, lag_min in (("noosa_head", 0), ("tin_can_bay", 44)):
        rows = []
        t = datetime(year, 1, 1, 3, 10, tzinfo=TZ) + timedelta(minutes=lag_min)
        high = True
        k = 0
        while t.year == year:
            spring = 1 + 0.35 * math.cos(2 * math.pi * k / 57)   # ~fortnightly cycle
            h = (1.55 if high else 0.35) * spring if high else 0.35 / spring
            rows.append({"t": t.isoformat(timespec="minutes"), "h": round(h, 2), "type": "H" if high else "L"})
            t += timedelta(minutes=372 + (5 if k % 2 else 0)); high = not high; k += 1
        write_json(CACHE / f"tides_{sid}_{year}.json", rows)
    write_json(CACHE / "weather.json", weather)
    write_json(CACHE / "marine.json", marine)
    write_json(CACHE / "alerts.json", [{
        "id": "synthetic-1", "title": f"[{label}] Severe erosion – Inskip barge landing beach access tracks",
        "summary": "Synthetic placeholder alert used for offline testing.", "link": "https://parks.qld.gov.au/park-alerts/",
        "published": (t0 + timedelta(days=1)).isoformat(), "severity": "warning", "locations": ["inskip_ocean", "inskip_bay"], "source": "QPWS park alerts"}])
    write_json(CACHE / "bom_coastal.json", {"issued": None, "areas": {}, "warning_active": False, "synthetic": label})
    write_json(CACHE / "bom_obs.json", {"station": "94584", "name": "Double Island Point", "obs": [], "synthetic": label})
    OBS.mkdir(parents=True, exist_ok=True)
    (OBS / "observations.jsonl").write_text(json.dumps({
        "id": "synthetic-obs-1", "source": "synthetic", "source_name": f"{label}", "provenance": "automated",
        "url": None, "section": "Tin Can Bay", "report_date": (t0 + timedelta(days=1)).strftime("%Y-%m-%d"),
        "catch_date": None, "catch_date_note": "synthetic", "species": ["whiting", "flathead", "mackerel"],
        "locations": ["tin_can_bay", "inskip_ocean"], "text": "SYNTHETIC: whiting on the flats, flathead in the drains, mackerel near Inskip Point.",
        "credit": label, "ingested_at": datetime.now(TZ).isoformat(timespec="seconds")}) + "\n", encoding="utf-8")
    return label


if __name__ == "__main__":
    print(make())
