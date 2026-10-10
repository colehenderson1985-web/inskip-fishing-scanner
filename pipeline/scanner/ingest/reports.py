"""Public fishing-report ingestion → observations (append-only JSONL).

Observation shape:
{
  id, source, source_name, provenance, url, report_date, catch_date, catch_date_note,
  species: [...], locations: [...], text (excerpt), credit, ingested_at
}
Observations are deduplicated by id (sha of source+url+section).
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime
from email.utils import parsedate_to_datetime

import feedparser
from bs4 import BeautifulSoup

from ..util import OBS, StepResult, TZ, archive_raw, get, log, now, sha
from . import extract

MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"], start=1)}


def load_observations() -> list[dict]:
    p = OBS / "observations.jsonl"
    if not p.exists():
        return []
    with open(p, "r", encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def append_observations(new: list[dict]) -> int:
    OBS.mkdir(parents=True, exist_ok=True)
    existing = {o["id"] for o in load_observations()}
    added = 0
    with open(OBS / "observations.jsonl", "a", encoding="utf-8") as f:
        for o in new:
            if o["id"] in existing:
                continue
            f.write(json.dumps(o, ensure_ascii=False) + "\n")
            existing.add(o["id"])
            added += 1
    return added


def make_observation(source: str, source_name: str, provenance: str, url: str | None,
                     report_date: datetime, text: str, credit: str, section: str = "") -> dict:
    catch_date, note = extract.infer_catch_date(text, report_date)
    return {
        "id": sha(f"{source}|{url}|{section}|{report_date.date()}"),
        "source": source, "source_name": source_name, "provenance": provenance,
        "url": url, "section": section,
        "report_date": report_date.strftime("%Y-%m-%d"),
        "catch_date": catch_date, "catch_date_note": note,
        "species": extract.find_species(text),
        "locations": extract.find_locations(text),
        "text": text[:1500],
        "credit": credit,
        "ingested_at": now().isoformat(timespec="seconds"),
    }


# ---------------------------------------------------------------- Coastwatch

def _coastwatch_date(title: str) -> datetime | None:
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", title)
    if not m:
        return None
    mon = MONTHS.get(m.group(2).lower())
    if not mon:
        return None
    return datetime(int(m.group(3)), mon, int(m.group(1)), tzinfo=TZ)


def fetch_coastwatch(cfg: dict) -> tuple[list[dict], StepResult]:
    try:
        r = get(cfg["list_url"], timeout=30)
        archive_raw("coastwatch", "list.html", r.content)
        soup = BeautifulSoup(r.content, "lxml")
        candidates = []
        for a in soup.find_all("a", href=True):
            txt = a.get_text(" ", strip=True)
            if txt.lower().startswith("fishing report for"):
                d = _coastwatch_date(txt)
                if d:
                    candidates.append((d, a["href"], txt))
        if not candidates:
            raise RuntimeError("no report links found on list page")
        candidates.sort(reverse=True)
        d, href, title = candidates[0]
        time.sleep(cfg.get("crawl_delay_s", 10))
        art = get(href, timeout=30)
        archive_raw("coastwatch", f"{d.date()}.html", art.content)
        sections = split_coastwatch_sections(art.content)
        obs = []
        for name in cfg["sections"]:
            body = next((v for k, v in sections.items() if k.lower().startswith(name.lower().split("/")[0].strip())), None)
            if body:
                obs.append(make_observation("coastwatch", cfg["name"], cfg["provenance"], href, d, body,
                                            cfg["credit"], section=name))
        return obs, StepResult("coastwatch", True, items=len(obs), note=title)
    except Exception as e:  # noqa: BLE001
        log.exception("coastwatch failed")
        return [], StepResult("coastwatch", False, error=str(e))


def split_coastwatch_sections(html: bytes) -> dict[str, str]:
    soup = BeautifulSoup(html, "lxml")
    for t in soup.find_all(["table", "script", "style", "figure", "img"]):
        t.decompose()
    sections: dict[str, str] = {}
    current = None
    buf: list[str] = []
    for el in soup.find_all(["h2", "h3", "p"]):
        if el.name in ("h2", "h3"):
            if current and buf:
                sections[current] = " ".join(buf).strip()
            current = el.get_text(" ", strip=True).strip("*").strip()
            buf = []
        elif current:
            txt = el.get_text(" ", strip=True)
            if txt and not txt.lower().startswith("ph"):
                buf.append(txt)
    if current and buf:
        sections[current] = " ".join(buf).strip()
    return sections


# ---------------------------------------------------------------- Atom / RSS feeds

def fetch_feed(source_id: str, cfg: dict, match_terms: list[str] | None = None, limit: int = 3) -> tuple[list[dict], StepResult]:
    try:
        r = get(cfg["feed_url"], timeout=30)
        archive_raw(source_id, "feed.xml", r.content)
        feed = feedparser.parse(r.content)
        obs = []
        for e in feed.entries[:15]:
            text = BeautifulSoup(e.get("content", [{}])[0].get("value", "") if e.get("content") else e.get("summary", ""), "lxml").get_text(" ", strip=True)
            title = e.get("title", "")
            if match_terms and not any(t in (title + " " + text).lower() for t in match_terms):
                continue
            d = None
            for k in ("published", "updated"):
                if e.get(k):
                    try:
                        d = parsedate_to_datetime(e[k]).astimezone(TZ)
                        break
                    except Exception:  # noqa: BLE001
                        try:
                            d = datetime.fromisoformat(e[k].replace("Z", "+00:00")).astimezone(TZ)
                            break
                        except Exception:  # noqa: BLE001
                            pass
            if not d:
                continue
            obs.append(make_observation(source_id, cfg["name"], cfg["provenance"], e.get("link"), d,
                                        f"{title}. {text}", cfg["credit"], section=title[:80]))
            if len(obs) >= limit:
                break
        return obs, StepResult(source_id, True, items=len(obs))
    except Exception as e:  # noqa: BLE001
        log.exception("%s failed", source_id)
        return [], StepResult(source_id, False, error=str(e))


def fetch_all(sources: dict) -> tuple[int, list[StepResult]]:
    results = []
    new: list[dict] = []
    o, r = fetch_coastwatch(sources["reports"]["coastwatch"]); new += o; results.append(r)
    o, r = fetch_feed("fishos", sources["reports"]["fishos"]); new += o; results.append(r)
    nt = sources["reports"]["noosa_today"]
    o, r = fetch_feed("noosa_today", nt, match_terms=nt.get("match_terms")); new += o; results.append(r)
    added = append_observations(new)
    return added, results
