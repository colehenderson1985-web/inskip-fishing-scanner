"""Bureau of Meteorology via anonymous FTP (documented, non-commercial use).

- IDQ11290.xml  Queensland coastal waters forecast (all zones). We keep the
  K'gari Coast and Sunshine Coast Waters areas: wind, seas, swell, weather and
  the warning summary per forecast period.
- IDQ60801.<station>.json  latest observations (Double Island Point AWS).

FTP is the sanctioned route; HTTP JSON under /fwo/ is robots-disallowed and
BOM has blocked non-browser user agents in the past. Everything here degrades
to cached data on failure.
"""
from __future__ import annotations

import ftplib
import io
import json
import re
import xml.etree.ElementTree as ET

from ..util import CACHE, StepResult, archive_raw, log, read_json, write_json, now


def _ftp_get(host: str, path: str, name: str, timeout: int = 40) -> bytes:
    buf = io.BytesIO()
    with ftplib.FTP(host, timeout=timeout) as ftp:
        ftp.login()  # anonymous
        ftp.cwd(path)
        ftp.retrbinary(f"RETR {name}", buf.write)
    return buf.getvalue()


def fetch_coastal(sources: dict, zone_names: list[str]) -> tuple[dict, StepResult]:
    cfg = sources["weather"]["bom_ftp"]
    try:
        raw = _ftp_get(cfg["host"], cfg["path"], cfg["coastal_waters_product"])
        archive_raw("bom", cfg["coastal_waters_product"], raw)
        parsed = parse_coastal_xml(raw, zone_names)
        parsed["fetched_at"] = now().isoformat(timespec="seconds")
        write_json(CACHE / "bom_coastal.json", parsed)
        return parsed, StepResult("bom_coastal", True, items=len(parsed.get("areas", {})))
    except Exception as e:  # noqa: BLE001
        log.exception("bom coastal failed")
        cached = read_json(CACHE / "bom_coastal.json", {})
        return cached, StepResult("bom_coastal", False, items=len(cached.get("areas", {})), error=str(e))


def parse_coastal_xml(raw: bytes, zone_names: list[str]) -> dict:
    root = ET.fromstring(raw)
    issued = None
    amoc = root.find("amoc")
    if amoc is not None:
        it = amoc.find("issue-time-local")
        issued = it.text if it is not None else None
    areas: dict[str, dict] = {}
    for area in root.iter("area"):
        desc = area.get("description", "")
        if not any(z.lower().split("(")[0].strip() in desc.lower() for z in zone_names):
            continue
        periods = []
        for fp in area.findall("forecast-period"):
            p = {"index": fp.get("index"), "start": fp.get("start-time-local"), "end": fp.get("end-time-local")}
            for t in fp.findall("text"):
                p[t.get("type")] = (t.text or "").strip()
            periods.append(p)
        warning = ""
        for t in area.iter("text"):
            if t.get("type", "").startswith("warning"):
                warning = (t.text or "").strip()
        areas[desc] = {"periods": periods, "warning_summary": warning, "aac": area.get("aac")}
    return {"issued": issued, "areas": areas, "warning_active": _warning_active(areas)}


def _warning_active(areas: dict) -> bool:
    for a in areas.values():
        w = a.get("warning_summary", "").lower()
        if w and "no warning" not in w and "nil" not in w:
            return True
        for p in a.get("periods", []):
            ws = (p.get("warning_summary_footer") or p.get("warning_summary") or "").lower()
            if ws and "no warning" not in ws:
                return True
    return False


def fetch_obs(sources: dict, station: str) -> tuple[dict, StepResult]:
    cfg = sources["weather"]["bom_ftp"]
    name = cfg["obs_product_template"].format(station=station)
    try:
        raw = _ftp_get(cfg["host"], cfg["path"], name)
        archive_raw("bom", name, raw)
        j = json.loads(raw)
        data = j.get("observations", {}).get("data", [])
        obs = [{
            "t": d.get("local_date_time_full"), "wind_dir": d.get("wind_dir"),
            "wind_kn": _kn(d.get("wind_spd_kmh")), "gust_kn": _kn(d.get("gust_kmh")),
            "pressure_hpa": d.get("press_msl"), "temp_c": d.get("air_temp"),
            "rain_mm": d.get("rain_trace"),
        } for d in data[:72]]
        out = {"station": station, "name": j.get("observations", {}).get("header", [{}])[0].get("name"),
               "obs": obs, "fetched_at": now().isoformat(timespec="seconds")}
        write_json(CACHE / "bom_obs.json", out)
        return out, StepResult("bom_obs", True, items=len(obs))
    except Exception as e:  # noqa: BLE001
        log.exception("bom obs failed")
        cached = read_json(CACHE / "bom_obs.json", {})
        return cached, StepResult("bom_obs", False, items=len(cached.get("obs", [])), error=str(e))


def _kn(kmh):
    try:
        return round(float(kmh) / 1.852, 1)
    except (TypeError, ValueError):
        return None


def pressure_trend(obs: list[dict]) -> str | None:
    """Trend over the last ~6 h of observations: rising / steady / falling / falling_fast."""
    vals = [o["pressure_hpa"] for o in obs if o.get("pressure_hpa") not in (None, "-")]
    if len(vals) < 6:
        return None
    try:
        latest, earlier = float(vals[0]), float(vals[min(len(vals) - 1, 36)])
    except ValueError:
        return None
    d = latest - earlier
    if d <= -3:
        return "falling_fast"
    if d < -1:
        return "falling"
    if d > 1:
        return "rising"
    return "steady"
