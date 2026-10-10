"""Rules-based extraction of species / locations / dates from report text.

Deterministic and transparent. An LLM can be layered on later for tricky
posts; this handles the common patterns in tackle-shop prose.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta

from ..util import TZ

SPECIES_TERMS: dict[str, list[str]] = {
    "tailor": ["tailor", "chopper", "choppers", "greenback"],
    "dart": ["dart"],
    "whiting": ["whiting"],
    "bream": ["bream"],
    "flathead": ["flathead", "flatty", "flatties", "lizard", "lizards"],
    "mulloway": ["mulloway", "jew", "jewfish", "jewie", "jewies", "soapie", "soapies"],
    "trevally": ["trevally", "gt", "gts", "golden trevally", "giant trevally"],
    "mangrove_jack": ["mangrove jack", "jack", "jacks"],
    "grunter": ["grunter", "javelin"],
    "snapper": ["snapper", "squire"],
    "cobia": ["cobia", "black kingfish"],
    "mackerel": ["mackerel", "spotties", "spotty", "spotted mackerel", "school mackerel", "schoolies", "spanish"],
}

LOCATION_TERMS: dict[str, list[str]] = {
    "inskip_ocean": ["inskip", "inskip point", "the bar", "wide bay bar", "big mick"],
    "inskip_bay": ["pelican bay", "inskip bay side", "the straits", "straits", "ida island", "panikan"],
    "rainbow_town": ["rainbow beach", "rainbow", "town beach", "carlo sandblow"],
    "rainbow_north": ["rainbow beach", "northern beach", "north of town"],
    "carlo_point": ["carlo point", "carlo"],
    "tin_can_bay": ["tin can bay", "tin can", "snapper creek", "crab creek", "norman point", "the creeks", "the flats", "dinnies", "kauri creek"],
    "rainbow_to_dip": ["mudlo", "double island", "dip", "southern beach"],
    "dip_north": ["double island point", "dip", "the lighthouse", "wolf rock", "the point"],
    "teewah": ["teewah", "freshwater", "cooloola"],
}

WORD = re.compile(r"[a-z]+(?:\s[a-z]+)?")


def find_species(text: str) -> list[str]:
    t = " " + re.sub(r"[^a-z0-9 ]", " ", text.lower()) + " "
    hits = []
    for sid, terms in SPECIES_TERMS.items():
        for term in terms:
            if f" {term} " in t or f" {term}s " in t:
                hits.append(sid)
                break
    return hits


def find_locations(text: str) -> list[str]:
    t = " " + re.sub(r"[^a-z0-9 ]", " ", text.lower()) + " "
    hits = []
    for lid, terms in LOCATION_TERMS.items():
        for term in terms:
            if f" {term} " in t:
                hits.append(lid)
                break
    return hits


def infer_catch_date(text: str, report_date: datetime) -> tuple[str | None, str]:
    """Best-effort catch date from relative phrases. Returns (iso_date|None, note)."""
    t = text.lower()
    if re.search(r"\b(this morning|today|overnight|last night)\b", t):
        return report_date.strftime("%Y-%m-%d"), "stated today"
    if "yesterday" in t:
        return (report_date - timedelta(days=1)).strftime("%Y-%m-%d"), "stated yesterday"
    m = re.search(r"\b(over|on) the weekend\b", t)
    if m:
        back = (report_date.weekday() + 1) % 7 + 1  # days back to last Sunday
        return (report_date - timedelta(days=back)).strftime("%Y-%m-%d"), "stated weekend (approx)"
    if re.search(r"\b(this week|past week|last week|the week)\b", t):
        return (report_date - timedelta(days=3)).strftime("%Y-%m-%d"), "within the week (approx)"
    return None, "catch date not stated — treated as report-week"


def sentences_mentioning(text: str, terms: list[str]) -> list[str]:
    out = []
    for s in re.split(r"(?<=[.!?])\s+", text):
        sl = s.lower()
        if any(term in sl for term in terms):
            out.append(s.strip())
    return out
