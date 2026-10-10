"""Great Sandy Marine Park zones (Zoning Plan 2024) as GeoJSON for the map.

Source: Queensland Government ArcGIS REST (ParksMarineProtectedAreas, layer 15).
Fetched for the region bbox and cached in data/cache/zones.geojson; refreshed
when the cache is older than ~90 days.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from ..util import BROWSER_UA, CACHE, StepResult, archive_raw, get, log

URL = "https://spatial-gis.information.qld.gov.au/arcgis/rest/services/Environment/ParksMarineProtectedAreas/MapServer/15/query"


def fetch_zones(bbox: list[list[float]], max_age_days: int = 90) -> StepResult:
    out = CACHE / "zones.geojson"
    if out.exists() and (time.time() - out.stat().st_mtime) < max_age_days * 86400:
        return StepResult("gsmp_zones", True, items=-1, note="cached")
    try:
        (s, w), (n, e) = bbox
        params = {
            "geometry": f"{w},{s},{e},{n}", "geometryType": "esriGeometryEnvelope", "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects", "outFields": "zone_id,zone_name,zone_type",
            "outSR": "4326", "f": "geojson", "geometryPrecision": "5",
        }
        r = get(URL, params=params, timeout=90, ua=BROWSER_UA)
        gj = r.json()
        feats = gj.get("features", [])
        if not feats:
            raise RuntimeError("no zone features returned")
        archive_raw("zones", "gsmp_zones.geojson", r.content)
        out.write_text(json.dumps(gj), encoding="utf-8")
        return StepResult("gsmp_zones", True, items=len(feats))
    except Exception as e:  # noqa: BLE001
        log.exception("zones fetch failed")
        return StepResult("gsmp_zones", out.exists(), items=0, error=str(e), note="using cached file" if out.exists() else None)
