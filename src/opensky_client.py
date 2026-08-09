"""Thin client for OpenSky Network's free, anonymous /states/all endpoint.

Anonymous rate limit observed at ~400 requests/day (verified live before
building this). At the chosen 15-minute polling cadence (96 requests/day)
there's wide margin -- no signup/API key needed.
"""

import requests

from config import OPENSKY_STATES_URL

# Index positions within each state vector, per OpenSky's documented schema.
# https://openskynetwork.github.io/opensky-api/rest.html#response
FIELDS = [
    "icao24", "callsign", "origin_country", "time_position", "last_contact",
    "longitude", "latitude", "baro_altitude", "on_ground", "velocity",
    "true_track", "vertical_rate", "sensors", "geo_altitude", "squawk",
    "spi", "position_source", "category",
]


def fetch_states():
    """Returns a list of dicts, one per currently-tracked aircraft."""
    resp = requests.get(OPENSKY_STATES_URL, timeout=30)
    resp.raise_for_status()
    payload = resp.json()
    raw_states = payload.get("states") or []

    states = []
    for row in raw_states:
        state = dict(zip(FIELDS, row))
        if state.get("callsign"):
            state["callsign"] = state["callsign"].strip()
        states.append(state)
    return states, payload.get("time")
