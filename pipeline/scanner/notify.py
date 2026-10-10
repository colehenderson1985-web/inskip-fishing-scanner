"""Push notifications via ntfy (https://ntfy.sh) — free, no account.

Setup: install the ntfy app, subscribe to the secret topic (GitHub secret NTFY_TOPIC).
Morning run (before 12:00 AEST): today's peak bite windows, always.
Evening run: tomorrow's windows, only if tomorrow's best score >= rules.alerts.evening_min_score.
Each push carries a "Share to WhatsApp" action that opens WhatsApp with the message pre-filled.

Usage: python -m scanner.notify [--force] [--day today|tomorrow]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse

import requests

from .util import DATA, TZ, load_yaml, log, now, read_json

SITE = "https://colehenderson1985-web.github.io/inskip-fishing-scanner/"


def nice_date(d: str) -> str:
    from datetime import datetime
    dt = datetime.strptime(d, "%Y-%m-%d")
    return dt.strftime("%a %-d %b")


def bite_message(latest: dict, day_index: int) -> tuple[str, str, int]:
    """Return (title, body, best_score) mirroring the site's WhatsApp share."""
    day = latest["days"][day_index]
    b = day["brief"]
    locs = {l["id"]: l for l in latest["locations"]}
    sps = {s["id"]: s for s in latest["species"]}
    lines, seen = [], set()
    for o in day["top"]:
        key = (o["location"], o["window"]["start"])
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"• {o['window']['start']}–{o['window']['end']} {sps[o['species']].get('short', sps[o['species']]['name'])} @ {locs[o['location']]['short']} ({o['score']})")
        if len(lines) >= 4:
            break
    loc = locs.get((b.get("best_location") or {}).get("id"))
    ref = (loc or {}).get("tide_ref", "noosa_head")
    tides = " · ".join(f"{t['type']} {t['t'][11:16]}" for t in latest["tides"].get(ref, []) if t["t"].startswith(day["date"]))
    c = day["top"][0]["conditions"] if day["top"] else None
    wx = f"Wind {c.get('wind_dir') or ''} {c['wind_kn']} kn" + (f", seas {c['seas_m']} m" if c and c.get("seas_m") is not None else "") if c else ""
    best = day["top"][0]["score"] if day["top"] else 0
    when = "Today" if day_index == 0 else "Tomorrow"
    title = f"{when}: {b['headline']}" + (f" — {sps[day['top'][0]['species']].get('short')} @ {locs[day['top'][0]['location']]['short']} {day['top'][0]['window']['start']}" if day["top"] else "")
    body = "\n".join(x for x in [
        f"🎣 Inskip Scanner — {nice_date(day['date'])}",
        f"{b['headline']}. {b['summary']}",
        "", "Peak bite windows:", *lines, "",
        f"Tides ({ref.replace('_', ' ')}): {tides}",
        wx,
        f"{b['confidence']} confidence · suitability, not a guarantee",
        f"{SITE}#/day/{day['date']}",
    ] if x is not None)
    return title, body, best


def send(topic: str, title: str, body: str, *, priority: str = "default", tags: str = "fishing_pole_and_fish") -> bool:
    wa = "https://wa.me/?text=" + urllib.parse.quote(body)
    headers = {
        "Title": title,
        "Priority": priority,
        "Tags": tags,
        "Click": SITE,
        "Actions": f"view, Share to WhatsApp, {wa}, clear=true; view, Open scanner, {SITE}",
        "Content-Type": "text/plain; charset=utf-8",
    }
    # ntfy headers must be latin-1 safe; use the X-Title/X-Message-encoding trick for unicode titles
    if any(ord(ch) > 255 for ch in title):
        import base64
        headers["Title"] = "=?UTF-8?B?" + base64.b64encode(title.encode("utf-8")).decode() + "?="
    r = requests.post(f"https://ntfy.sh/{topic}", data=body.encode("utf-8"), headers=headers, timeout=20)
    log.info("ntfy %s: %s", r.status_code, r.text[:120])
    return r.ok


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="send even if below threshold")
    ap.add_argument("--day", choices=["today", "tomorrow", "auto"], default="auto")
    a = ap.parse_args(argv)
    topic = os.environ.get("NTFY_TOPIC", "").strip()
    if not topic:
        print("NTFY_TOPIC not set — skipping push")
        return 0
    latest = read_json(DATA / "latest.json")
    if not latest:
        print("no latest.json")
        return 0
    rules = load_yaml("rules.yaml").get("alerts", {})
    hour = now().hour
    day_index = 0 if a.day == "today" else 1 if a.day == "tomorrow" else (0 if hour < 12 else 1)
    title, body, best = bite_message(latest, day_index)
    if day_index == 1 and not a.force and best < rules.get("evening_min_score", 70):
        print(f"tomorrow's best {best} < threshold — no evening push")
        return 0
    if day_index == 0 and not a.force and best < rules.get("morning_min_score", 0):
        print(f"today's best {best} < threshold — no morning push")
        return 0
    prio = "high" if best >= rules.get("high_priority_score", 85) else "default"
    ok = send(topic, title, body, priority=prio)
    print("sent" if ok else "failed")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
