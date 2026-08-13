"""Quick correctness tests for the parts of the pipeline that don't need a
live API call or the full 91MB aircraft database.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from emissions import classify_phase, classify_region
from features import airline_from_callsign, dark_aircraft_check


def test_classify_phase():
    assert classify_phase({"on_ground": True, "vertical_rate": 0}) == "ground"
    assert classify_phase({"on_ground": False, "vertical_rate": 5.0}) == "climb"
    assert classify_phase({"on_ground": False, "vertical_rate": -5.0}) == "descent"
    assert classify_phase({"on_ground": False, "vertical_rate": 0.1}) == "cruise"
    assert classify_phase({"on_ground": False, "vertical_rate": None}) == "cruise"


def test_classify_region_east_africa():
    # Nairobi JKIA is roughly -1.3, 36.9
    assert classify_region({"latitude": -1.3, "longitude": 36.9}) == "east_africa"


def test_classify_region_outside_all_boxes():
    # middle of the Pacific -- shouldn't match any defined region
    assert classify_region({"latitude": 0, "longitude": -160}) == "other"


def test_airline_from_callsign():
    assert airline_from_callsign("ETH302") == "ETH"
    assert airline_from_callsign("kqa100") == "KQA"
    assert airline_from_callsign("N12345") is None  # private aircraft tail number, no airline prefix pattern
    assert airline_from_callsign("") is None
    assert airline_from_callsign(None) is None


def test_dark_aircraft_check_flags_watch_region_only():
    previous_seen = {
        "abc123": {"lat": 45.5, "lon": 35.0, "altitude": 10000, "callsign": "TEST123"},  # Black Sea watch region
        "def456": {"lat": 51.5, "lon": -0.1, "altitude": 9000, "callsign": "NORMAL1"},   # London, not a watch region
        "ghi789": {"lat": 45.5, "lon": 35.0, "altitude": 500, "callsign": "LOWALT"},     # watch region but too low -> probably just landed
    }
    flagged, _ = dark_aircraft_check([], previous_seen, all_current_icao24s=set())
    flagged_ids = {f["icao24"] for f in flagged}
    assert flagged_ids == {"abc123"}


def test_dark_aircraft_check_excludes_normal_landings():
    # jkl999 was airborne at cruise altitude over the watch region last time,
    # but reappears on the ground this snapshot (e.g. it landed at Tel Aviv)
    # -- must NOT be flagged, even though it's absent from the airborne view.
    previous_seen = {
        "jkl999": {"lat": 32.0, "lon": 34.8, "altitude": 2000, "callsign": "ELY358"},  # eastern Mediterranean
    }
    flagged, _ = dark_aircraft_check([], previous_seen, all_current_icao24s={"jkl999"})
    assert flagged == []


if __name__ == "__main__":
    test_classify_phase()
    test_classify_region_east_africa()
    test_classify_region_outside_all_boxes()
    test_airline_from_callsign()
    test_dark_aircraft_check_flags_watch_region_only()
    test_dark_aircraft_check_excludes_normal_landings()
    print("ALL TESTS PASSED")
