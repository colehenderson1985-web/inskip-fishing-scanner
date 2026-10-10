"""QPWS park alerts (RSS) — closures, erosion, access hazards."""
from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime

import feedparser

from ..util import CACHE, StepResult, TZ, archive_raw, get, iso, log, read_json, write_json


def fetch_alerts(sources: dict, rules: dict) -> tuple[list[dict], StepResult]:
    cfg = sources["alerts"]["qpws_rss"]
    terms = [t.lower() for t in cfg["match_terms"]]
    close_kw = [k.lower() for k in rules["safety"]["alert_keywords_close"]]
    warn_kw = [k.lower() for k in rules["safety"]["alert_keywords_warn"]]
    try:
        r = get(cfg["url"], timeout=30)
        archive_raw("qpws", "parkalerts-sunshine-coast.xml", r.content)
        feed = feedparser.parse(r.content)
        out = []
        for e in feed.entries:
            text = f"{e.get('title','')} {e.get('summary','')}".lower()
            if not any(t in text for t in terms):
                continue
            pub = None
            try:
                pub = parsedate_to_datetime(e.get("published", "")).astimezone(TZ)
            except Exception:  # noqa: BLE001
                pass
            sev = "info"
            access_kw = ("beach", "beach access", "4wd", "track", "road", "vehicle", "ramp", "recreation area closed", "area closed", "camping area")
            if "wilderness trail" in text or "walking track" in text or "hiking" in text:
                access_kw = ()
            if any(k in text for k in close_kw) and any(k in text for k in access_kw):
                sev = "closure"
            elif any(k in text for k in warn_kw) or any(k in text for k in close_kw):
                sev = "warning"
            out.append({
                "id": e.get("id") or e.get("link"),
                "title": e.get("title", "").strip(),
                "summary": _clean(e.get("summary", ""))[:600],
                "link": e.get("link"),
                "published": iso(pub),
                "severity": sev,
                "locations": _match_locations(text),
                "source": "QPWS park alerts",
            })
        out.sort(key=lambda a: a.get("published") or "", reverse=True)
        write_json(CACHE / "alerts.json", out)
        return out, StepResult("qpws_alerts", True, items=len(out))
    except Exception as e:  # noqa: BLE001
        log.exception("qpws alerts failed")
        cached = read_json(CACHE / "alerts.json", [])
        return cached, StepResult("qpws_alerts", False, items=len(cached), error=str(e))


LOC_TERMS = {
    "inskip": ["inskip_ocean", "inskip_bay"],
    "pelican bay": ["inskip_bay"],
    "rainbow beach": ["rainbow_town", "rainbow_north"],
    "double island": ["dip_north", "rainbow_to_dip"],
    "mudlo": ["rainbow_to_dip"],
    "leisha": ["dip_north"],
    "teewah": ["teewah"],
    "cooloola": ["rainbow_to_dip", "dip_north", "teewah"],
    "tin can": ["tin_can_bay", "carlo_point"],
    "carlo": ["carlo_point"],
}


def _match_locations(text: str) -> list[str]:
    ids: list[str] = []
    for term, locs in LOC_TERMS.items():
        if term in text:
            for l in locs:
                if l not in ids:
                    ids.append(l)
    return ids


def _clean(html: str) -> str:
    import re
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()
