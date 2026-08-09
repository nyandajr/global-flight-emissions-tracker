"""Shared constants for the flight emissions pipeline."""

from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
AIRCRAFT_DB_PATH = REPO_DIR / "data" / "cache" / "aircraftDatabase.csv"
AIRCRAFT_LOOKUP_CACHE = REPO_DIR / "data" / "cache" / "icao24_to_category.json"
HISTORY_CSV = REPO_DIR / "data" / "history.csv"
DASHBOARD_JSON = REPO_DIR / "docs" / "data.json"

OPENSKY_STATES_URL = "https://opensky-network.org/api/states/all"

# Standard, publicly documented conversion factor: kg CO2 emitted per kg of
# jet fuel burned (same figure used by ICAO's carbon calculator methodology).
KG_CO2_PER_KG_FUEL = 3.16

# Fuel burn rates in kg/hour, by broad aircraft category and flight phase.
# These are approximate, publicly-known figures (ballpark averages derived
# from published EUROCONTROL/ICAO aircraft emissions databank ranges for
# representative types in each category) -- NOT measured, NOT manufacturer
# certified data. This is a modeled estimate, same honesty framing as
# hormuz-strait-monitor's "AIS-transit-count proxy, not measured tonnage".
FUEL_BURN_KG_PER_HOUR = {
    "widebody":     {"climb": 9500, "cruise": 6500, "descent": 2800},
    "narrowbody":   {"climb": 3800, "cruise": 2500, "descent": 1300},
    "regional_jet": {"climb": 1800, "cruise": 1100, "descent":  600},
    "turboprop":    {"climb":  900, "cruise":  550, "descent":  350},
    "piston":       {"climb":   80, "cruise":   55, "descent":   40},
    "unknown":      {"climb": 3800, "cruise": 2500, "descent": 1300},  # falls back to narrowbody-ish, the most common category worldwide
}

# Specific typecode -> category, for the aircraft we can identify precisely.
# Anything not listed here falls back to a category inferred from the
# aircraft database's icaoaircrafttype field (engine count + power plant).
TYPECODE_CATEGORY = {
    # narrowbody
    "A19N": "narrowbody", "A20N": "narrowbody", "A21N": "narrowbody",
    "A318": "narrowbody", "A319": "narrowbody", "A320": "narrowbody", "A321": "narrowbody",
    "B737": "narrowbody", "B738": "narrowbody", "B739": "narrowbody",
    "B37M": "narrowbody", "B38M": "narrowbody", "B39M": "narrowbody",
    # widebody
    "A332": "widebody", "A333": "widebody", "A339": "widebody",
    "A345": "widebody", "A346": "widebody", "A359": "widebody", "A35K": "widebody",
    "A388": "widebody",
    "B762": "widebody", "B763": "widebody", "B764": "widebody",
    "B772": "widebody", "B773": "widebody", "B77L": "widebody", "B77W": "widebody",
    "B788": "widebody", "B789": "widebody", "B78X": "widebody",
    "B744": "widebody", "B748": "widebody",
    # regional jets
    "E170": "regional_jet", "E175": "regional_jet", "E190": "regional_jet", "E195": "regional_jet",
    "CRJ2": "regional_jet", "CRJ7": "regional_jet", "CRJ9": "regional_jet",
    # turboprops (common on East African / regional short-hop routes)
    "AT72": "turboprop", "AT76": "turboprop", "AT45": "turboprop",
    "DH8A": "turboprop", "DH8B": "turboprop", "DH8C": "turboprop", "DH8D": "turboprop",
}

# icaoaircrafttype prefix (from the OpenSky aircraft DB) -> fallback category,
# used when a typecode isn't in the table above. Format is roughly
# <landing-gear><engine-count><engine-type>, e.g. "L2J" = land, 2 engines, jet.
ICAOAIRCRAFTTYPE_FALLBACK = {
    "J": "narrowbody",   # jet, unknown specifics -> most common jet class worldwide
    "T": "turboprop",
    "P": "piston",
}

# Rough regional bins by lat/lon bounding box, for the global breakdown.
# East Africa is deliberately called out on its own, same "zoom into one
# region within a global picture" pattern as hormuz-strait-monitor.
REGIONS = {
    "east_africa":     {"lat": (-12, 15),  "lon": (29, 51)},
    "europe":          {"lat": (35, 71),   "lon": (-25, 40)},
    "north_america":   {"lat": (15, 72),   "lon": (-170, -50)},
    "east_asia":       {"lat": (18, 53),   "lon": (100, 150)},
    "middle_east":     {"lat": (12, 40),   "lon": (34, 63)},
    "south_asia":      {"lat": (5, 35),    "lon": (60, 92)},
    "oceania":         {"lat": (-47, -10), "lon": (110, 180)},
    "south_america":   {"lat": (-56, 13),  "lon": (-82, -34)},
}
