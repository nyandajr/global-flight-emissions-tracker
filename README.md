# Global Flight Emissions Tracker

Live global aircraft tracking with modeled per-flight CO2 emission estimates,
updated every 15 minutes. Built on OpenSky Network's free, anonymous
`/states/all` endpoint (~400 requests/day budget, no signup required).

**[Live dashboard](https://nyandajr.github.io/global-flight-emissions-tracker/)**

## Why global, not East-Africa-scoped

This project started as an East-Africa flight tracker, but a live coverage
check killed that design: a bounding box over the whole region returned only
2 tracked aircraft, versus 735 in a same-size European test box. OpenSky
depends on volunteer-run ADS-B ground receivers, and East Africa has very
few of them — real air traffic there is much higher than "2," the receivers
just aren't there to see it. That gap is the same shape of problem found
earlier in this portfolio with Twelve Data's NSE Kenya coverage and NewsAPI's
East Africa coverage.

So the project tracks globally, with East Africa called out as one
highlighted region within the global picture — the same "zoom into one area
within a global feed" pattern `hormuz-strait-monitor` uses for its strait.
The regional coverage gap itself is now a tracked, honest data point (see
"Infrastructure inequality" below) instead of a silent limitation.

## Methodology — modeled estimate, not measured emissions

OpenSky's live feed gives position, altitude, and velocity — not aircraft
type or scheduled route. So instead of a simple distance × flat-rate calc,
emissions are estimated **per flight phase**:

1. Aircraft type is resolved by joining each `icao24` against OpenSky's free
   downloadable aircraft metadata database (~520k aircraft, cached locally).
2. Flight phase (climb / cruise / descent / ground) is classified from each
   aircraft's current vertical rate and altitude.
3. Fuel burn is estimated from a category × phase lookup table (climb burns
   markedly more than cruise, which burns more than descent).
4. CO2 = fuel burned × 3.16 (the standard kg CO2 per kg jet fuel factor).

This is explicitly a **modeled estimate**, not measured emissions — same
honesty framing as `hormuz-strait-monitor`'s AIS-transit-count throughput
proxy. As a sanity check: the pipeline's first live run estimated ~18,700
tonnes CO2 for one 15-minute global snapshot, against a back-of-envelope
expectation of ~25,700 tonnes from published global aviation emissions
figures — same order of magnitude, not off by 10x.

## Features

- **Airline emissions leaderboard** — CO2/hour by airline, parsed from each
  flight's ICAO callsign prefix (e.g. `ETH` = Ethiopian, `KQA` = Kenya
  Airways, `AAL` = American).
- **Fleet efficiency clustering** — unsupervised k-means clustering of
  airlines by their currently-airborne fleet's aircraft-category mix,
  labeling clusters as modern / mixed / older-or-regional fleet. Works on a
  single snapshot, unlike trend forecasting, which needs weeks of history
  first.
- **Dark-aircraft flags** — aircraft that were airborne and clearly visible
  in the previous snapshot but are missing now, *if* their last known
  position was inside a small set of watch regions. Deliberately labeled as
  a low-confidence heuristic: ADS-B receiver handoff gaps are far more
  common than a genuine transponder-off event.
- **Infrastructure inequality** — live aircraft count by region, an honest
  look at where ADS-B ground coverage is dense (Europe, North America) vs
  sparse (East Africa) — the coverage gap as a tracked finding, not a bug.
- **Phase-of-flight snapshot** — % of the tracked global fleet currently in
  climb / cruise / descent, right now.

## What's deliberately not built yet

Time-series emissions **forecasting** (as opposed to the current per-flight
estimate) needs weeks/months of accumulated history to mean anything — same
reasoning as the planned Linear Regression → LSTM upgrade path in
`ea-financial-tracker`. Revisit once `data/history.csv` has real depth.

## Running it

```bash
pip install -r requirements.txt
python src/aircraft_db.py   # one-time: builds the aircraft type cache (~91MB download)
python src/pipeline.py      # one pipeline run
```

`vm_automation/run_and_push.py` is the VM-cron entry point — same
sync-hard → run → content-aware-commit → force-push pattern as the other
trackers in this portfolio, deployed at 15-minute cadence.
