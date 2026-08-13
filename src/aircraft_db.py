"""Builds a SQLite-indexed icao24 -> {category, typecode, operator} lookup
from OpenSky's free aircraft metadata database.

Originally this cached the full ~520k-aircraft lookup as one JSON dict loaded
entirely into memory on every pipeline run. On the VM's 1GB-RAM Always Free
instance, that habit (36MB JSON -> a much larger in-memory Python dict, on
top of the rest of the pipeline) contributed to an OOM event on 2026-08-13
that killed cron.service itself and silently took down all 7 repos' VM
automation for two days. SQLite fixes this at the root: each run only fetches
the ~10k aircraft actually seen in that snapshot via one indexed query,
instead of ever holding all 520k in Python memory.
"""

import csv
import sqlite3

from config import (
    AIRCRAFT_DB_PATH,
    AIRCRAFT_LOOKUP_CACHE,
    ICAOAIRCRAFTTYPE_FALLBACK,
    TYPECODE_CATEGORY,
)

# Same cache path as before, but now a SQLite file instead of a JSON blob.
DB_PATH = AIRCRAFT_LOOKUP_CACHE.with_suffix(".sqlite")


def _categorize(typecode, icaoaircrafttype):
    if typecode in TYPECODE_CATEGORY:
        return TYPECODE_CATEGORY[typecode]
    if icaoaircrafttype:
        engine_type = icaoaircrafttype[-1]
        if engine_type in ICAOAIRCRAFTTYPE_FALLBACK:
            return ICAOAIRCRAFTTYPE_FALLBACK[engine_type]
    return "unknown"


def build_lookup_cache():
    """Reads the full aircraft database CSV once and writes it to an indexed
    SQLite file. Run this at setup time and periodically (e.g. monthly) to
    refresh -- not on every pipeline run.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE aircraft (
            icao24 TEXT PRIMARY KEY,
            category TEXT,
            typecode TEXT,
            operator TEXT
        )
    """)

    count = 0
    with open(AIRCRAFT_DB_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        batch = []
        for row in reader:
            icao24 = row.get("icao24", "").strip().lower()
            if not icao24:
                continue
            typecode = row.get("typecode", "").strip().upper()
            icaoaircrafttype = row.get("icaoaircrafttype", "").strip().upper()
            operator = row.get("operatoricao", "").strip().upper() or row.get("operator", "").strip()
            batch.append((icao24, _categorize(typecode, icaoaircrafttype), typecode, operator))
            count += 1
            if len(batch) >= 5000:
                conn.executemany("INSERT OR REPLACE INTO aircraft VALUES (?,?,?,?)", batch)
                batch = []
        if batch:
            conn.executemany("INSERT OR REPLACE INTO aircraft VALUES (?,?,?,?)", batch)

    conn.commit()
    conn.close()

    print(f"[aircraft_db] cached {count} aircraft to {DB_PATH}")


def lookup_many(icao24_list):
    """Returns {icao24: {category, typecode, operator}} for just the given
    icao24s -- e.g. the ~10k aircraft in one live snapshot, not all 520k.
    """
    if not DB_PATH.exists():
        build_lookup_cache()

    icao24_list = [i.strip().lower() for i in icao24_list if i]
    if not icao24_list:
        return {}

    conn = sqlite3.connect(str(DB_PATH))
    result = {}
    # SQLite's default parameter limit is 999 -- chunk the IN clause.
    chunk_size = 900
    for i in range(0, len(icao24_list), chunk_size):
        chunk = icao24_list[i:i + chunk_size]
        placeholders = ",".join("?" * len(chunk))
        rows = conn.execute(
            f"SELECT icao24, category, typecode, operator FROM aircraft WHERE icao24 IN ({placeholders})",
            chunk,
        ).fetchall()
        for icao24, category, typecode, operator in rows:
            result[icao24] = {"category": category, "typecode": typecode, "operator": operator}
    conn.close()
    return result


if __name__ == "__main__":
    build_lookup_cache()
