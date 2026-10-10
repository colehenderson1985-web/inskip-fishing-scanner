"""Tide predictions.

Primary: Maritime Safety Queensland yearly high/low predictions (BOM-produced,
CC BY 4.0) on data.qld.gov.au. We discover the current year's resource via the
CKAN API and read rows from the CKAN datastore (JSON), falling back to the CSV
download. Rows: Date dd/mm/yyyy, Time HH:MM, Ind 1 (high) / -1 (low), Reading m.
Results are cached in data/cache so the pipeline keeps working if the portal is down.

Fallback: Open-Meteo Marine `sea_level_height_msl` hourly series → local extrema,
labelled "modelled" (lower confidence).
"""
from __future__ import annotations

import csv
import io
import re
from datetime import datetime

from ..util import BROWSER_UA, CACHE, StepResult, TZ, archive_raw, get, log, now, read_json, write_json

CKAN = "https://www.data.qld.gov.au/api/3/action"

DATE_PATTERNS = ["%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M", "%d-%m-%Y %H:%M"]


def _parse_dt(s: str) -> datetime | None:
    s = s.strip()
    for p in DATE_PATTERNS:
        try:
            return datetime.strptime(s, p).replace(tzinfo=TZ)
        except ValueError:
            continue
    return None


def _row(date: str, time: str, ind: str, reading: str) -> dict | None:
    dt = _parse_dt(f"{date} {time}")
    if not dt:
        return None
    try:
        h = float(reading)
    except (TypeError, ValueError):
        return None
    i = str(ind).strip().upper()
    kind = "H" if i in ("1", "H", "HIGH", "HW") else "L" if i in ("-1", "L", "LOW", "LW") else None
    return {"t": dt.isoformat(timespec="minutes"), "h": round(h, 2), "type": kind}


def parse_records(records: list[dict]) -> list[dict]:
    rows = []
    for r in records:
        k = {str(a).strip().lower(): b for a, b in r.items()}
        row = _row(k.get("date", ""), k.get("time", ""), k.get("ind", ""), k.get("reading", ""))
        if row:
            rows.append(row)
    return _finish(rows)


def parse_hilo_csv(text: str) -> list[dict]:
    rows: list[dict] = []
    reader = csv.reader(io.StringIO(text.lstrip("﻿")))
    header = None
    for raw in reader:
        cells = [c.strip() for c in raw]
        if not any(cells):
            continue
        if header is None and any(c.lower() == "date" for c in cells):
            header = [c.lower() for c in cells]
            continue
        if header and len(cells) >= 4:
            d = dict(zip(header, cells))
            row = _row(d.get("date", ""), d.get("time", ""), d.get("ind", ""), d.get("reading", ""))
        else:
            # tolerant positional fallback: date, time, ind, reading
            row = _row(cells[0], cells[1], cells[2], cells[3]) if len(cells) >= 4 else None
            if not row and len(cells) >= 3:
                row = _row(cells[0], cells[1], "", cells[2])
        if row:
            rows.append(row)
    return _finish(rows)


def _finish(rows: list[dict]) -> list[dict]:
    rows.sort(key=lambda r: r["t"])
    for i, r in enumerate(rows):
        if r["type"] is None:
            ref = rows[i - 1]["h"] if i > 0 else (rows[i + 1]["h"] if i + 1 < len(rows) else None)
            r["type"] = "H" if (ref is not None and r["h"] >= ref) else "L"
    return rows


def _find_resource(dataset: str, year: int) -> dict | None:
    r = get(f"{CKAN}/package_show", params={"id": dataset}, timeout=30, ua=BROWSER_UA)
    for res in r.json().get("result", {}).get("resources", []):
        name = f"{res.get('name') or ''} {res.get('url') or ''}"
        if str(year) in name:
            return res
    return None


def fetch_station(station_id: str, cfg: dict, year: int) -> tuple[list[dict], StepResult]:
    cache = CACHE / f"tides_{station_id}_{year}.json"
    cached = read_json(cache)
    if cached and len(cached) > 300:
        return cached, StepResult(f"tides_{station_id}", True, items=len(cached), note="cached")
    try:
        res = _find_resource(cfg["hilo_dataset"], year)
        if not res:
            raise RuntimeError(f"no {year} resource in {cfg['hilo_dataset']}")
        rows: list[dict] = []
        note = ""
        try:
            r = get(f"{CKAN}/datastore_search", params={"resource_id": res["id"], "limit": 5000}, timeout=60, ua=BROWSER_UA)
            archive_raw("tides", f"{station_id}_{year}_datastore.json", r.content)
            rows = parse_records(r.json().get("result", {}).get("records", []))
            note = f"datastore {res['id']}"
        except Exception as e:  # noqa: BLE001
            log.warning("datastore failed for %s (%s); trying CSV", station_id, e)
        if len(rows) < 300:
            r = get(res["url"], timeout=60, ua=BROWSER_UA)
            archive_raw("tides", f"{station_id}_{year}.csv", r.content)
            ct = r.headers.get("content-type", "")
            if "html" in ct.lower():
                raise RuntimeError(f"CSV download returned HTML ({ct}) from {res['url']}")
            rows = parse_hilo_csv(r.content.decode("utf-8", errors="replace"))
            note = res["url"]
        if len(rows) < 300:
            raise RuntimeError(f"parsed only {len(rows)} tide rows for {station_id} {year}")
        write_json(cache, rows)
        return rows, StepResult(f"tides_{station_id}", True, items=len(rows), note=note)
    except Exception as e:  # noqa: BLE001
        log.exception("tide fetch failed for %s", station_id)
        return cached or [], StepResult(f"tides_{station_id}", False, items=len(cached or []), error=str(e))


def extrema_from_series(times: list[str], heights: list[float | None]) -> list[dict]:
    """Local maxima/minima of an hourly sea-level series (fallback, 'modelled'). Times → AEST-aware ISO."""
    out = []
    for i in range(1, len(heights) - 1):
        a, b, c = heights[i - 1], heights[i], heights[i + 1]
        if None in (a, b, c):
            continue
        t = times[i] if re.search(r"[+-]\d{2}:\d{2}$", times[i]) else times[i] + "+10:00"
        if b >= a and b > c:
            out.append({"t": t, "h": round(b, 2), "type": "H", "modelled": True})
        elif b <= a and b < c:
            out.append({"t": t, "h": round(b, 2), "type": "L", "modelled": True})
    return out


def fetch_all(sources: dict, marine: dict | None = None) -> tuple[dict, list[StepResult]]:
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
            mp = marine.get("bar") or next(iter(marine.values()), None)
            if mp and mp.get("sea_level_height_msl"):
                rows = extrema_from_series(mp["time"], mp["sea_level_height_msl"])
                results.append(StepResult(f"tides_{sid}_fallback", True, items=len(rows), note="open-meteo modelled sea level"))
        out[sid] = rows
    return out, results
