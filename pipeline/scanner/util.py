"""Shared helpers: paths, time zone, HTTP, raw archiving, config loading."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
import yaml

log = logging.getLogger("scanner")

ROOT = Path(os.environ.get("SCANNER_ROOT", Path(__file__).resolve().parents[2]))
CONFIG = ROOT / "config"
DATA = ROOT / "data"
RAW = DATA / "raw"
OBS = DATA / "observations"
DERIVED = DATA / "derived"
CACHE = DATA / "cache"

TZ = ZoneInfo("Australia/Brisbane")  # AEST, no daylight saving
UA = "InskipFishingScanner/0.1 (+https://github.com/colehenderson1985-web/inskip-fishing-scanner; personal non-commercial)"
BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"


def now() -> datetime:
    return datetime.now(TZ)


def today() -> datetime:
    return now().replace(hour=0, minute=0, second=0, microsecond=0)


def iso(dt: datetime | None) -> str | None:
    return dt.isoformat(timespec="seconds") if dt else None


def load_yaml(name: str) -> dict:
    with open(CONFIG / name, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_config() -> dict:
    return {
        "locations": load_yaml("locations.yaml"),
        "species": load_yaml("species.yaml"),
        "rules": load_yaml("rules.yaml"),
        "sources": load_yaml("sources.yaml"),
    }


_session: requests.Session | None = None


def http() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({"User-Agent": UA, "Accept": "*/*"})
    return _session


def get(url: str, *, timeout: int = 30, ua: str | None = None, retries: int = 1, **kw) -> requests.Response:
    headers = {}
    if ua:
        headers = {"User-Agent": ua, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                   "Accept-Language": "en-AU,en;q=0.9", "Cache-Control": "no-cache"}
    last = None
    for attempt in range(retries + 1):
        try:
            r = http().get(url, timeout=timeout, headers=headers, **kw)
            r.raise_for_status()
            return r
        except requests.HTTPError as e:  # retry 5xx once
            last = e
            if attempt < retries and e.response is not None and e.response.status_code >= 500:
                import time; time.sleep(5); continue
            raise
    raise last  # pragma: no cover


def archive_raw(category: str, name: str, content: bytes | str) -> Path:
    """Store an untouched copy of a fetched payload under data/raw/YYYY-MM-DD/."""
    d = RAW / today().strftime("%Y-%m-%d")
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{category}__{name}"
    if isinstance(content, str):
        content = content.encode("utf-8")
    p.write_bytes(content)
    return p


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, default=str)
    os.replace(tmp, path)


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def sha(s: str | bytes) -> str:
    if isinstance(s, str):
        s = s.encode("utf-8")
    return hashlib.sha256(s).hexdigest()[:16]


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def hours_since(ts: str | None) -> float | None:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ)
        return (now() - dt).total_seconds() / 3600
    except ValueError:
        return None


class StepResult(dict):
    """Uniform result for an ingest step; feeds health.json."""

    def __init__(self, source: str, ok: bool, items: int = 0, error: str | None = None,
                 fetched_at: datetime | None = None, note: str | None = None):
        super().__init__(source=source, ok=ok, items=items, error=error,
                         fetched_at=iso(fetched_at or now()), note=note)
