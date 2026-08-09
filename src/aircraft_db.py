"""Builds and loads a compact icao24 -> {category, typecode, operator} lookup
from OpenSky's free aircraft metadata database, so the pipeline never has to
read the full ~91MB CSV on every run -- only when the cache is rebuilt.
"""

import csv
import json

from config import (
    AIRCRAFT_DB_PATH,
    AIRCRAFT_LOOKUP_CACHE,
    ICAOAIRCRAFTTYPE_FALLBACK,
    TYPECODE_CATEGORY,
)


def _categorize(typecode, icaoaircrafttype):
    if typecode in TYPECODE_CATEGORY:
        return TYPECODE_CATEGORY[typecode]
    if icaoaircrafttype:
        # e.g. "L2J" -> engine type is the last character
        engine_type = icaoaircrafttype[-1]
        if engine_type in ICAOAIRCRAFTTYPE_FALLBACK:
            return ICAOAIRCRAFTTYPE_FALLBACK[engine_type]
    return "unknown"


def build_lookup_cache():
    """Reads the full aircraft database CSV once and writes a compact JSON
    lookup. Run this at setup time and periodically (e.g. monthly) to refresh
    -- not on every pipeline run.
    """
    lookup = {}
    with open(AIRCRAFT_DB_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            icao24 = row.get("icao24", "").strip().lower()
            if not icao24:
                continue
            typecode = row.get("typecode", "").strip().upper()
            icaoaircrafttype = row.get("icaoaircrafttype", "").strip().upper()
            operator = row.get("operatoricao", "").strip().upper() or row.get("operator", "").strip()
            lookup[icao24] = {
                "category": _categorize(typecode, icaoaircrafttype),
                "typecode": typecode,
                "operator": operator,
            }

    AIRCRAFT_LOOKUP_CACHE.parent.mkdir(parents=True, exist_ok=True)
    with open(AIRCRAFT_LOOKUP_CACHE, "w") as f:
        json.dump(lookup, f)

    print(f"[aircraft_db] cached {len(lookup)} aircraft to {AIRCRAFT_LOOKUP_CACHE}")
    return lookup


def load_lookup():
    if not AIRCRAFT_LOOKUP_CACHE.exists():
        return build_lookup_cache()
    with open(AIRCRAFT_LOOKUP_CACHE) as f:
        return json.load(f)


if __name__ == "__main__":
    build_lookup_cache()
