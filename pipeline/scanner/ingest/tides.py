"""Tide predictions.

Primary: Maritime Safety Queensland yearly high/low CSVs (BOM-produced) on
data.qld.gov.au, discovered via the CKAN API and cached in data/cache so the
pipeline keeps working if the portal is down.

Fallback: Open-Meteo Marine `sea_level_height_msl` hourly series → local
extrema, labelled "modelled" (lower confidence).

The MSQ CSV layout is parsed tolerantly: any row with a parseable date/time,
a numeric height and (optionally) an H/L marker is accepted. The first live
run archives the raw file so the parser can be tightened against reality.
"""
from __future__ import annotations

import csv
import io
import re
from datetime import datetime, timedelta

from ..util import CACHE, StepResult, TZ, archive_raw, get, log, now, read_json, write_json

CKAN = "https://www.data.qld.gov.au/api/3/action/package_show"

DATE_PATTERNS = [
    "%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S", "%d-%m-%Y %H:%M", "%d %b %Y %H:%M",
]


def _parse_dt(s: str) -> datetime | None:
    s = s.strip().replace("  ", " ")
    for p in DATE_PATTERNS:
        try:
            return datetime.strptime(s, p).replace(tzinfo=TZ)
        except ValueError:
            continue
    return None


def parse_hilo_csv(text: str) -> list[dict]:
    """Return [{'t': iso, 'h': float, 'type': 'H'|'L'}], sorted by time."""
    rows: list[dict] = []
    reader = csv.reader(io.StringIO(text))
    for raw in reader:
        if not raw or all(not c.strip() for c in raw):
            continue
        cells = [c.strip() for c in raw]
        dt = None
        # try combined datetime in any cell, else date + time in adjacent cells
        for i, c in enumerate(cells):
            dt = _parse_dt(c)
            if dt:
                break
            if i + 1 < len(cells):
                dt = _parse_dt(f"{c} {cells[i+1]}")
                if dt:
                    break
        if not dt:
            continue
        h = None
        for c in cells:
            if re.fullmatch(r"-?\d+(\.\d+)?", c):
                v = float(c)
                if -1 < v < 5:
                    h = v
        if h is None:
            continue
        kind = None
        for c in cells:
            cu = c.upper()
            if cu in ("H", "HIGH", "HW", "HIGH WATER"):
                kind = "H"
            elif cu in ("L", "LOW", "LW", "LOW WATER"):
                kind = "L"
        rows.append({"t": dt.isoformat(timespec="minutes"), "h": h, "type": kind})
    rows.sort(key=lambda r: r["t"])
    # infer H/L from neighbours where missing
    for i, r in enumerate(rows):
        if r["type"] is None:
            prev_h = rows[i - 1]["h"] if i > 0 else None
            next_h = rows[i + 1]["h"] if i + 1 < len(rows) else None
            ref = prev_h if prev_h is not None else next_h
            r["type"] = "H" if (ref is not None and r["h"] >= ref) else "L"
    return rows


def _discover_hilo_url(dataset: str, year: int) -> str | None:
    r = get(CKAN, params={"id": dataset}, timeout=30, ua=None)
    j = r.json()
    for res in j.get("result", {}).get("resources", []):
        name = (res.get("name") or "") + " " + (res.get("url") or "")
        if str(year) in name and res.get("url", "").lower().endswith(".csv"):
            return res["url"]
    return None


def fetch_station(station_id: str, cfg: dict, year: int) -> tuple[list[dict], StepResult]:
    cache = CACHE / f"tides_{station_id}_{year}.json"
    cached = read_json(cache)
    if cached and len(cached) > 300:
        return cached, StepResult(f"tides_{station_id}", True, items=len(cached), note="cached")
    try:
        url = cfg.get(f"hilo_{year}_url") or _discover_hilo_url(cfg["hilo_dataset"], year)
        if not url:
            raise RuntimeError(f"no {year} hi/lo CSV found for {cfg['hilo_dataset']}")
        r = get(url, timeout=60)
        archive_raw("tides", f"{station_id}_{year}.csv", r.content)
        rows = parse_hilo_csv(r.content.decode("utf-8", errors="replace"))
        if len(rows) < 300:
            raise RuntimeError(f"parsed only {len(rows)} tide rows from {url}")
        write_json(cache, rows)
        return rows, StepResult(f"tides_{station_id}", True, items=len(rows), note=url)
    except Exception as e:  # noqa: BLE001
        log.exception("tide fetch failed for %s", station_id)
        return cached or [], StepResult(f"tides_{station_id}", False, items=len(cached or []), error=str(e))


def extrema_from_series(times: list[str], heights: list[float | None]) -> list[dict]:
    """Local maxima/minima of an hourly sea-level series (fallback, 'modelled')."""
    out = []
    for i in range(1, len(heights) - 1):
        a, b, c = heights[i - 1], heights[i], heights[i + 1]
        if None in (a, b, c):
            continue
        if b >= a and b > c:
            out.append({"t": times[i], "h": round(b, 2), "type": "H", "modelled": True})
        elif b <= a and b < c:
            out.append({"t": times[i], "h": round(b, 2), "type": "L", "modelled": True})
    return out


def fetch_all(sources: dict, marine: dict | None = None) -> tuple[dict, list[StepResult]]:
    """Return {station_id: [hilo...]} covering this and (if available) next year."""
    results: list[StepResult] = []
    out: dict[str, list[dict]] = {}
    y = now().year
    for sid, cfg in sources["tides"]["msq"]["stations"].items():
        rows, res = fetch_station(sid, cfg, y)
        results.append(res)
        if now().month == 12:
            nxt, res2 = fetch_station(sid, cfg, y + 1)
            if res2["ok"]:
                rows = rows + nxt
            results.append(res2)
        if not rows and marine:
            # fallback: modelled sea level at the bar/ocean point
            mp = marine.get("bar") or next(iter(marine.values()), None)
            if mp and mp.get("sea_level_height_msl"):
                rows = extrema_from_series(mp["time"], mp["sea_level_height_msl"])
                results.append(StepResult(f"tides_{sid}_fallback", True, items=len(rows), note="open-meteo modelled sea level"))
        out[sid] = rows
    return out, results


def window(rows: list[dict], start: datetime, end: datetime) -> list[dict]:
    s, e = start.isoformat(timespec="minutes"), end.isoformat(timespec="minutes")
    return [r for r in rows if s <= r["t"] <= e]
