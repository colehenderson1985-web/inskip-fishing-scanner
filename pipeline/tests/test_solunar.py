"""Almanac-style lunar rating and solunar bite times."""
from datetime import datetime, timedelta

from scanner.ingest import astro, solunar
from scanner.util import TZ

LAT, LON = -25.88, 153.09


def _day(y, m, d):
    return datetime(y, m, d, tzinfo=TZ)


def test_overhead_transit_sits_between_moonrise_and_moonset():
    a = astro.day_astro(_day(2026, 10, 13), LAT, LON)
    sol = a["solunar"]
    rise, set_ = datetime.fromisoformat(a["moonrise"]), datetime.fromisoformat(a["moonset"])
    over = [datetime.fromisoformat(m["centre"]) for m in sol["majors"] if m["kind"] == "overhead"]
    assert over, sol["majors"]
    midpoint = rise + (set_ - rise) / 2
    assert abs((over[0] - midpoint).total_seconds()) < 45 * 60


def test_full_moon_overhead_near_midnight_and_rated_best():
    a = astro.day_astro(_day(2026, 10, 26), LAT, LON)   # full moon ~26 Oct 2026
    sol = a["solunar"]
    assert sol["rating"] == "Best"
    over = [m for m in sol["majors"] if m["kind"] == "overhead"]
    assert over and (over[0]["centre"][11:13] in ("22", "23") or over[0]["centre"][11:13] in ("00", "01"))


def test_ratings_cover_the_cycle_and_majors_are_two_hours():
    seen = set()
    for i in range(30):
        sol = astro.day_astro(_day(2026, 11, 1) + timedelta(days=i), LAT, LON)["solunar"]
        seen.add(sol["rating"])
        for m in sol["majors"]:
            span = datetime.fromisoformat(m["end"]) - datetime.fromisoformat(m["start"])
            assert span == timedelta(hours=2)
        assert 1 <= len(sol["majors"]) <= 2
    assert {"Best", "Poor"} <= seen


def test_bite_times_are_aest_without_daylight_saving():
    for m in (1, 7):
        sol = astro.day_astro(_day(2027, m, 15), LAT, LON)["solunar"]
        assert all(p["centre"].endswith("+10:00") for p in sol["majors"] + sol["minors"])


def test_moon_distance_in_physical_range():
    d = [solunar.moon_distance_km(_day(2026, 1, 1) + timedelta(days=i)) for i in range(365)]
    assert 355_000 < min(d) < 362_000
    assert 404_000 < max(d) < 407_500


def test_window_overlapping_major_scores_higher_lunar_factor():
    sol = astro.day_astro(_day(2026, 10, 13), LAT, LON)["solunar"]
    c = datetime.fromisoformat(sol["majors"][0]["centre"])
    hit = solunar.overlap(c - timedelta(hours=1), c + timedelta(hours=1), sol)
    miss = solunar.overlap(c + timedelta(hours=4), c + timedelta(hours=5), sol)
    assert hit["major"] and not miss["major"]
    assert solunar.lunar_factor(sol, hit) > solunar.lunar_factor(sol, miss)
    assert 0.4 <= solunar.lunar_factor(sol, miss) <= 0.95
