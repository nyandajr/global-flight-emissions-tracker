"""Phase-of-flight classification, fuel burn, and CO2 estimation.

This is a MODELED ESTIMATE, not measured emissions -- same honesty framing
as hormuz-strait-monitor's AIS-transit-count proxy. It uses each aircraft's
current altitude trend (a single live data point per aircraft, not a
reconstructed flight path) and a category-average fuel burn table.
"""

from config import FUEL_BURN_KG_PER_HOUR, KG_CO2_PER_KG_FUEL, REGIONS

# m/s vertical rate thresholds for climb/descent vs level flight.
# 2.5 m/s ~= 492 ft/min, a standard-ish cutoff for "clearly climbing/descending"
# vs cruise-level minor altitude noise.
VERTICAL_RATE_THRESHOLD = 2.5


def classify_phase(state):
    if state.get("on_ground"):
        return "ground"
    vr = state.get("vertical_rate")
    if vr is None:
        return "cruise"  # no vertical rate reported -> assume level flight
    if vr > VERTICAL_RATE_THRESHOLD:
        return "climb"
    if vr < -VERTICAL_RATE_THRESHOLD:
        return "descent"
    return "cruise"


def classify_region(state):
    lat, lon = state.get("latitude"), state.get("longitude")
    if lat is None or lon is None:
        return None
    for name, box in REGIONS.items():
        lat_min, lat_max = box["lat"]
        lon_min, lon_max = box["lon"]
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return name
    return "other"


def enrich_state(state, aircraft_lookup):
    icao24 = (state.get("icao24") or "").strip().lower()
    info = aircraft_lookup.get(icao24, {})
    category = info.get("category", "unknown")
    phase = classify_phase(state)
    region = classify_region(state)

    burn_rate_kg_per_hour = 0.0
    if phase != "ground":
        burn_rate_kg_per_hour = FUEL_BURN_KG_PER_HOUR.get(category, FUEL_BURN_KG_PER_HOUR["unknown"])[phase]

    return {
        **state,
        "category": category,
        "typecode": info.get("typecode", ""),
        "operator": info.get("operator", ""),
        "phase": phase,
        "region": region,
        "burn_rate_kg_per_hour": burn_rate_kg_per_hour,
        "co2_rate_kg_per_hour": burn_rate_kg_per_hour * KG_CO2_PER_KG_FUEL,
    }


def incremental_emissions_kg(enriched_states, interval_hours):
    """Total CO2 (kg) attributable to this snapshot interval, assuming each
    aircraft's current rate held for the whole interval since the last poll.
    An approximation, not a reconstructed flight path -- clearly labeled as
    such wherever this number surfaces downstream.
    """
    total_rate = sum(s["co2_rate_kg_per_hour"] for s in enriched_states)
    return total_rate * interval_hours
