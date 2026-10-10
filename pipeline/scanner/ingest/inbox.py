"""Report Inbox — admin-submitted reports (e.g. Facebook posts from tackle shops)
and group session ratings / catches.

Submissions arrive as a JSON payload (from the site's /admin form via
repository_dispatch, or a GitHub issue body) and become observations with
provenance recorded. The original text is archived untouched.

Payload:
{ "kind": "report" | "rating",
  "source": "<inbox source id>", "source_name": "...", "post_date": "YYYY-MM-DD",
  "text": "...", "url": "optional", "location": "optional loc id", "species": "optional",
  "rating": 1-5 (rating only), "date": "YYYY-MM-DD" (rating only) }
"""
from __future__ import annotations

import json
from datetime import datetime

from ..util import TZ, archive_raw, load_yaml, now, sha
from .reports import append_observations, make_observation


def ingest_payload(payload: dict) -> dict:
    archive_raw("inbox", f"{now().strftime('%H%M%S')}_{sha(json.dumps(payload, sort_keys=True))}.json",
                json.dumps(payload, ensure_ascii=False, indent=1))
    kind = payload.get("kind", "report")
    sources = {s["id"]: s for s in load_yaml("sources.yaml")["inbox_sources"]}
    src = sources.get(payload.get("source", "other"), sources["other"])
    if kind == "rating":
        d = datetime.strptime(payload["date"], "%Y-%m-%d").replace(tzinfo=TZ)
        obs = {
            "id": sha(f"rating|{payload.get('location')}|{payload.get('species')}|{payload['date']}|{payload.get('rating')}|{payload.get('text','')[:40]}"),
            "source": "group_rating", "source_name": "Group session rating", "provenance": "group_rating",
            "url": None, "section": "", "report_date": payload["date"], "catch_date": payload["date"],
            "catch_date_note": "session date", "species": [payload["species"]] if payload.get("species") else [],
            "locations": [payload["location"]] if payload.get("location") else [],
            "rating": int(payload.get("rating", 3)), "text": (payload.get("text") or "")[:500],
            "credit": "Group", "ingested_at": now().isoformat(timespec="seconds"),
        }
    else:
        d = datetime.strptime(payload["post_date"], "%Y-%m-%d").replace(tzinfo=TZ)
        obs = make_observation(src["id"], src["name"], src["provenance"], payload.get("url") or None,
                               d, payload["text"], f"{src['name']} (via admin)", section=payload.get("title", "")[:80])
        if payload.get("location") and payload["location"] not in obs["locations"]:
            obs["locations"].insert(0, payload["location"])
        if payload.get("species") and payload["species"] not in obs["species"]:
            obs["species"].insert(0, payload["species"])
    added = append_observations([obs])
    return {"added": added, "observation": obs}
