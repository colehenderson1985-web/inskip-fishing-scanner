"""End-to-end offline run on synthetic data: determinism, structure, gates."""
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))


@pytest.fixture(scope="module")
def latest(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("data")
    os.environ["SCANNER_ROOT"] = str(ROOT)
    # redirect data dir to tmp
    import scanner.util as u
    for name in ("DATA", "RAW", "OBS", "DERIVED", "CACHE"):
        setattr(u, name, tmp / name.lower())
    import importlib
    import scanner.ingest.open_meteo, scanner.ingest.tides, scanner.ingest.qpws, scanner.ingest.bom, scanner.ingest.reports, scanner.ingest.inbox, scanner.run
    for m in (scanner.ingest.open_meteo, scanner.ingest.tides, scanner.ingest.qpws, scanner.ingest.bom, scanner.ingest.reports, scanner.ingest.inbox, scanner.run):
        importlib.reload(m)
    from tests import synth
    importlib.reload(synth)
    synth.make()
    from scanner.run import refresh
    a = refresh(offline=True)
    b = refresh(offline=True)
    return a, b


def test_deterministic(latest):
    a, b = latest
    sa = [(r["location"], r["species"], r["score"]) for r in a["days"][0]["top"]]
    sb = [(r["location"], r["species"], r["score"]) for r in b["days"][0]["top"]]
    assert sa == sb


def test_structure(latest):
    a, _ = latest
    assert a["timezone"] == "Australia/Brisbane"
    assert len(a["days"]) == 8
    assert a["brief"]["summary"]
    assert all(0 <= r["score"] <= 100 for d in a["days"] for r in d["top"])
    assert all(r["colour"] in ("green", "amber", "red", "grey") for d in a["days"] for r in d["top"])
    assert all(r["explain"] for d in a["days"] for r in d["top"])
    assert set(a["health"]["sources"]) >= {"open_meteo_forecast"} or a["health"]["sources"] == {}


def test_conservation_park_limits_present(latest):
    a, _ = latest
    bay = next(l for l in a["locations"] if l["id"] == "inskip_bay")
    assert bay["line_limit"] == {"lines": 2, "hooks": 2}


def test_confidence_declines_with_horizon(latest):
    a, _ = latest
    order = {"high": 3, "medium": 2, "low": 1, "none": 0}
    d0 = max((order[r["confidence"]] for r in a["days"][0]["top"]), default=0)
    d6 = max((order[r["confidence"]] for r in a["days"][6]["top"]), default=0)
    assert d6 <= d0


def test_species_scanner_has_legal_links(latest):
    a, _ = latest
    assert a["rules"]["legal_source"].startswith("https://")
    for s in a["species"]:
        assert "possession" in s["legal"]
