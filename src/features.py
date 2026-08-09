"""The five differentiator features layered on top of the core emissions
pipeline: airline leaderboard, fleet efficiency clustering, dark-aircraft
detection, infrastructure-inequality stat, and phase-of-flight snapshot.
"""

import json
import re
from collections import Counter, defaultdict

import numpy as np
from sklearn.cluster import KMeans

CALLSIGN_AIRLINE_RE = re.compile(r"^([A-Z]{3})\d")
CATEGORIES = ["widebody", "narrowbody", "regional_jet", "turboprop", "piston", "unknown"]

# Aircraft going dark are only flagged if their last known position falls in
# one of these watch regions -- deliberately narrow, since disappearing from
# ADS-B coverage is far more often a receiver gap than a real event. This is
# a low-confidence heuristic, not a verified detection, and is labeled as such
# in the dashboard output.
WATCH_REGIONS = {
    "black_sea_ukraine":     {"lat": (44, 47),   "lon": (30, 40)},
    "eastern_mediterranean": {"lat": (31, 36),   "lon": (30, 36)},
    "red_sea":               {"lat": (12, 22),   "lon": (37, 44)},
    "south_china_sea":       {"lat": (5, 22),    "lon": (108, 118)},
}


def airline_from_callsign(callsign):
    if not callsign:
        return None
    match = CALLSIGN_AIRLINE_RE.match(callsign.strip().upper())
    return match.group(1) if match else None


def airline_leaderboard(enriched_states, top_n=15):
    """Total estimated CO2 rate (kg/hour) grouped by airline, derived from
    the callsign's ICAO 3-letter airline prefix.
    """
    totals = defaultdict(float)
    counts = Counter()
    for s in enriched_states:
        airline = airline_from_callsign(s.get("callsign"))
        if not airline:
            continue
        totals[airline] += s["co2_rate_kg_per_hour"]
        counts[airline] += 1

    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
    return [
        {"airline": code, "co2_kg_per_hour": round(rate, 1), "aircraft_tracked": counts[code]}
        for code, rate in ranked
    ]


def fleet_efficiency_clusters(enriched_states, n_clusters=3):
    """Unsupervised clustering (k-means) of airlines by their currently
    airborne fleet's category mix -- available immediately since it only
    needs one snapshot, unlike time-series forecasting which needs weeks of
    accumulated history first.
    """
    fleet_by_airline = defaultdict(Counter)
    for s in enriched_states:
        airline = airline_from_callsign(s.get("callsign"))
        if not airline:
            continue
        fleet_by_airline[airline][s["category"]] += 1

    # Only cluster airlines with a meaningful sample size.
    airlines = [a for a, c in fleet_by_airline.items() if sum(c.values()) >= 3]
    if len(airlines) < n_clusters:
        return []

    vectors = []
    for airline in airlines:
        counts = fleet_by_airline[airline]
        total = sum(counts.values())
        vectors.append([counts[cat] / total for cat in CATEGORIES])

    X = np.array(vectors)
    km = KMeans(n_clusters=n_clusters, n_init=10, random_state=42).fit(X)

    # Label clusters by their average widebody+narrowbody-modern share as a
    # rough "efficiency" proxy -- higher modern-jet share = "modern", higher
    # turboprop/piston/unknown share = "aging/regional".
    cluster_modern_share = {}
    for c in range(n_clusters):
        idx = [i for i, label in enumerate(km.labels_) if label == c]
        modern_share = np.mean([vectors[i][0] + vectors[i][1] for i in idx])  # widebody + narrowbody
        cluster_modern_share[c] = modern_share
    order = sorted(cluster_modern_share, key=cluster_modern_share.get, reverse=True)
    labels = {order[0]: "modern_fleet_mix", order[-1]: "older_or_regional_fleet_mix"}
    for c in order[1:-1]:
        labels[c] = "mixed_fleet"

    result = []
    for airline, label in zip(airlines, km.labels_):
        result.append({"airline": airline, "cluster": labels[label]})
    return result


def dark_aircraft_check(enriched_states, previous_seen):
    """Compares this snapshot's tracked aircraft against the previous run's,
    flagging ones that were airborne and clearly visible last time but are
    absent now, IF their last known position was inside a watch region.

    Explicitly a low-confidence heuristic: ADS-B coverage gaps between
    consecutive receiver handoffs are the far more common explanation than a
    deliberate transponder-off event. Labeled as such downstream.
    """
    current_seen = {}
    for s in enriched_states:
        icao24 = s.get("icao24")
        if not icao24 or s.get("on_ground"):
            continue
        current_seen[icao24] = {
            "lat": s.get("latitude"), "lon": s.get("longitude"),
            "altitude": s.get("baro_altitude"), "callsign": s.get("callsign"),
        }

    flagged = []
    for icao24, last in previous_seen.items():
        if icao24 in current_seen:
            continue
        if last.get("altitude") is None or last["altitude"] < 1000:
            continue  # was low/near airport, probably just landed
        lat, lon = last.get("lat"), last.get("lon")
        if lat is None or lon is None:
            continue
        for region, box in WATCH_REGIONS.items():
            lat_min, lat_max = box["lat"]
            lon_min, lon_max = box["lon"]
            if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
                flagged.append({
                    "icao24": icao24, "callsign": last.get("callsign"),
                    "last_region": region, "last_altitude_m": last["altitude"],
                })
                break

    return flagged, current_seen


def infrastructure_inequality(enriched_states):
    """Aircraft count per region right now -- an honest look at where ADS-B
    ground-receiver coverage is dense vs sparse, not just where traffic is.
    """
    counts = Counter(s["region"] for s in enriched_states if s.get("region"))
    return dict(counts.most_common())


def phase_snapshot(enriched_states):
    total = len(enriched_states)
    if total == 0:
        return {}
    counts = Counter(s["phase"] for s in enriched_states)
    return {phase: round(100 * n / total, 1) for phase, n in counts.items()}
