import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scanner import model  # noqa: E402
from scanner.util import TZ  # noqa: E402
from scanner.ingest.tides import parse_hilo_csv, extrema_from_series  # noqa: E402
from scanner.ingest import extract  # noqa: E402
from scanner.score import closure_active  # noqa: E402


def _hilo(day):
    base = day.replace(hour=1, minute=0)
    out, high = [], False
    for i in range(6):
        out.append({"t": (base + timedelta(hours=6.2 * i)).isoformat(timespec="minutes"), "h": 1.6 if high else 0.3, "type": "H" if high else "L"})
        high = not high
    return out


def test_tide_stage_classification():
    day = datetime(2026, 10, 11, tzinfo=TZ)
    hilo = _hilo(day)
    low = datetime.fromisoformat(hilo[0]["t"]); high = datetime.fromisoformat(hilo[1]["t"])
    assert model.tide_stage(low + timedelta(minutes=20), hilo)["stage"] == "low_turn"
    assert model.tide_stage(low + timedelta(minutes=100), hilo)["stage"] == "rising_early"
    assert model.tide_stage(high - timedelta(minutes=100), hilo)["stage"] == "rising_late"
    assert model.tide_stage(high - timedelta(minutes=20), hilo)["stage"] == "high_turn"
    assert model.tide_stage(high + timedelta(minutes=100), hilo)["stage"] == "falling_early"
    assert model.tide_stage(high + timedelta(hours=5), hilo)["stage"] == "falling_late"


def test_wind_exposure_east_facing_beach():
    loc = {"aspect_deg": 70, "shelter_from": ["W", "SW", "NW"], "shelter_degree": 0.8}
    assert model.wind_exposure(250, 15, loc)["relation"] == "offshore"
    assert model.wind_exposure(70, 15, loc)["relation"] == "onshore"
    assert model.wind_exposure(160, 15, loc)["relation"] == "cross"
    e = model.wind_exposure(225, 20, loc)
    assert e["effective_kn"] < 20  # sheltered from SW


def test_wind_factor_prefers_offshore():
    sp = {"wind": {"max_onshore_kn": 20}}
    off = model.wind_factor({"relation": "offshore", "effective_kn": 8}, sp, "surf_beach")
    on = model.wind_factor({"relation": "onshore", "effective_kn": 25}, sp, "surf_beach")
    assert off > on


def test_swell_band():
    sp = {"swell": {"min_m": 0.5, "ideal": [0.8, 1.8], "max_m": 2.5}}
    assert model.swell_factor(1.2, 11, sp, "surf_beach") >= 0.95
    assert model.swell_factor(3.2, 11, sp, "surf_beach") < 0.4
    assert model.swell_factor(3.2, 11, sp, "estuary") > 0.5


def test_season_factor():
    sp = {"season": {"peak": [5, 6, 7], "shoulder": [4, 8]}}
    assert model.season_factor(6, sp) == 1.0
    assert model.season_factor(8, sp) == 0.5
    assert model.season_factor(1, sp) == 0.15


def test_parse_hilo_csv_msq_layout():
    csv = "﻿Date,Time,Ind,Reading\n01/01/2026,06:07,1,2.090\n01/01/2026,12:42,-1,0.670\n02/01/2026,00:12,-1,0.330\n"
    rows = parse_hilo_csv(csv)
    assert len(rows) == 3 and rows[0]["type"] == "H" and rows[1]["type"] == "L" and rows[1]["h"] == 0.67
    assert rows[0]["t"] == "2026-01-01T06:07+10:00"


def test_parse_datastore_records():
    from scanner.ingest.tides import parse_records
    recs = [{"_id": 1, "Date": "01/01/2026", "Time": "06:07", "Ind": "1", "Reading": "2.090"},
            {"_id": 2, "Date": "01/01/2026", "Time": "12:42", "Ind": "-1", "Reading": "0.670"}]
    rows = parse_records(recs)
    assert [r["type"] for r in rows] == ["H", "L"]


def test_extrema_fallback():
    times = [f"2026-01-01T{h:02d}:00" for h in range(24)]
    import math
    h = [round(math.sin(2 * math.pi * i / 12.4), 2) for i in range(24)]
    ex = extrema_from_series(times, h)
    assert any(e["type"] == "H" for e in ex) and any(e["type"] == "L" for e in ex)
    assert all(e["modelled"] for e in ex)


def test_extract_species_and_locations():
    txt = "Good tailor and dart off Rainbow Beach this week; a few jew at Inskip Point after dark. Whiting on the flats at Tin Can Bay."
    sp = extract.find_species(txt)
    assert {"tailor", "dart", "mulloway", "whiting"} <= set(sp)
    locs = extract.find_locations(txt)
    assert "inskip_ocean" in locs and "tin_can_bay" in locs and "rainbow_town" in locs


def test_catch_date_inference():
    d = datetime(2026, 10, 9, tzinfo=TZ)
    assert extract.infer_catch_date("caught this morning", d)[0] == "2026-10-09"
    assert extract.infer_catch_date("yesterday's session", d)[0] == "2026-10-08"
    assert extract.infer_catch_date("nothing specific", d)[0] is None


def test_closure_wraps_year():
    c = {"annual": {"start": "11-01", "end": "01-31"}}
    assert closure_active(c, datetime(2026, 12, 15, tzinfo=TZ))
    assert closure_active(c, datetime(2027, 1, 10, tzinfo=TZ))
    assert not closure_active(c, datetime(2026, 6, 1, tzinfo=TZ))


def test_timezone_is_aest_no_dst():
    jan = datetime(2026, 1, 15, 12, tzinfo=TZ).utcoffset().total_seconds() / 3600
    jul = datetime(2026, 7, 15, 12, tzinfo=TZ).utcoffset().total_seconds() / 3600
    assert jan == 10 and jul == 10


def test_classify_report_vs_guide():
    assert extract.classify_kind("Weekly Fishing Report: Rainbow Beach 26 Sept", "...") == "report"
    assert extract.classify_kind("Choosing the Right Bait for Fishing Around Rainbow Beach", "Beach worms work well for whiting.") == "guide"
    assert extract.classify_kind("Big week on the beach", "Tailor were caught in numbers this week and jew landed after dark.") == "report"
