"""Orchestrates one pipeline run: fetch live states, enrich with aircraft
type + emissions, compute the five features, append history, write the
dashboard JSON.
"""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from aircraft_db import load_lookup
from config import DASHBOARD_JSON, HISTORY_CSV, REPO_DIR
from emissions import enrich_state, incremental_emissions_kg
from features import (
    airline_leaderboard,
    dark_aircraft_check,
    fleet_efficiency_clusters,
    infrastructure_inequality,
    phase_snapshot,
)
from opensky_client import fetch_states

INTERVAL_HOURS = 0.25  # matches the 15-minute VM cron cadence
LAST_SEEN_CACHE = REPO_DIR / "data" / "cache" / "last_seen.json"


def _load_last_seen():
    if not LAST_SEEN_CACHE.exists():
        return {}
    with open(LAST_SEEN_CACHE) as f:
        return json.load(f)


def _save_last_seen(current_seen):
    LAST_SEEN_CACHE.parent.mkdir(parents=True, exist_ok=True)
    with open(LAST_SEEN_CACHE, "w") as f:
        json.dump(current_seen, f)


def _cumulative_co2_kg_today():
    """Sums today's already-recorded incremental CO2 from history.csv, so the
    dashboard can show a running daily total, not just this snapshot.
    """
    if not HISTORY_CSV.exists():
        return 0.0
    today = datetime.now(timezone.utc).date().isoformat()
    total = 0.0
    with open(HISTORY_CSV, newline="") as f:
        for row in csv.DictReader(f):
            if row["generated_at"].startswith(today):
                total += float(row["incremental_co2_kg"])
    return total


def append_history(row):
    HISTORY_CSV.parent.mkdir(parents=True, exist_ok=True)
    is_new = not HISTORY_CSV.exists()
    with open(HISTORY_CSV, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if is_new:
            writer.writeheader()
        writer.writerow(row)


def write_dashboard(payload):
    DASHBOARD_JSON.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD_JSON.write_text(json.dumps(payload, indent=2))


def run():
    aircraft_lookup = load_lookup()
    raw_states, opensky_time = fetch_states()

    airborne = [s for s in raw_states if not s.get("on_ground")]
    enriched = [enrich_state(s, aircraft_lookup) for s in airborne]

    incremental_co2 = incremental_emissions_kg(enriched, INTERVAL_HOURS)

    previous_seen = _load_last_seen()
    dark_flags, current_seen = dark_aircraft_check(enriched, previous_seen)
    _save_last_seen(current_seen)

    now = datetime.now(timezone.utc)
    generated_at = now.isoformat()

    history_row = {
        "generated_at": generated_at,
        "aircraft_tracked": len(raw_states),
        "aircraft_airborne": len(airborne),
        "incremental_co2_kg": round(incremental_co2, 1),
        "dark_aircraft_flagged": len(dark_flags),
    }
    append_history(history_row)

    payload = {
        "generated_at": generated_at,
        "opensky_snapshot_time": opensky_time,
        "aircraft_tracked_total": len(raw_states),
        "aircraft_airborne": len(airborne),
        "co2_kg_today_cumulative": round(_cumulative_co2_kg_today(), 1),
        "co2_kg_this_snapshot": round(incremental_co2, 1),
        "phase_breakdown_pct": phase_snapshot(enriched),
        "region_aircraft_counts": infrastructure_inequality(enriched),
        "airline_leaderboard": airline_leaderboard(enriched),
        "fleet_efficiency_clusters": fleet_efficiency_clusters(enriched),
        "dark_aircraft_flags": dark_flags,
        "note": (
            "co2 figures are a MODELED ESTIMATE from live position/altitude data "
            "and category-average fuel burn rates -- not measured emissions. "
            "dark_aircraft_flags is a low-confidence heuristic: ADS-B receiver "
            "coverage gaps are far more common than genuine transponder-off events."
        ),
    }
    write_dashboard(payload)

    print(f"[pipeline] {len(raw_states)} aircraft tracked, {len(airborne)} airborne, "
          f"{round(incremental_co2, 1)} kg CO2 this snapshot, {len(dark_flags)} dark-aircraft flags")
    return payload


if __name__ == "__main__":
    run()
