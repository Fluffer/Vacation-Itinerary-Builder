# Stage 4 — v1 Standard Itinerary

> **Read first:** [`references/learnings.md`](../learnings.md)

## Inputs from prior stages
Stages 1-3 complete; `places[]` populated.

## What to produce
Populate `itinerary.v1_standard` — one array entry per day, each containing a `day_label` and a `rows[]` array. Active hours per day are capped at 14 (first activity start to last activity end). This is the "packed first-time-visitor" track; v2 (relaxed) and v3 (weather fallback) are derived from this in stage 5. Every place referenced by name must also carry a `place_key` matching a `places[].key` entry. Arrival day and departure day include airport buffer rows matching airline recommendation (typically 2hr domestic, 3hr international).

## Schema fields to fill
- `itinerary.v1_standard[].day_label` (e.g. `"Day 1 — Arrival"`)
- `itinerary.v1_standard[].rows[].time` (HH:MM 24h, or alpha-led label such as `"Sunrise"` / `"All day"`)
- `itinerary.v1_standard[].rows[].activity` (sentence)
- `itinerary.v1_standard[].rows[].route` (e.g. `"NAIA → Makati"`, or null for non-transit rows)
- `itinerary.v1_standard[].rows[].km` (number — for transit rows; null otherwise)
- `itinerary.v1_standard[].rows[].min` (integer — for transit rows; null otherwise)
- `itinerary.v1_standard[].rows[].cost_local` (integer, or `0` for free, or null for placeholder rows)
- `itinerary.v1_standard[].rows[].sgd` (number or null — leave null; budget sheet computes via formula)
- `itinerary.v1_standard[].rows[].notes`
- `itinerary.v1_standard[].rows[].place_key` (optional but RECOMMENDED — must match a `places[].key` if set)

## Quality bar
- Each row's `time` is `HH:MM` 24h OR an alpha-led short label. Stage 4 validator rejects malformed times (e.g. `"12345"`, `"x"`, `""`).
- Every row that references a place by name must also set `place_key` matching `places[].key`. Stage 4 rejects orphans.
- Each day has 6-12 rows: transit + visit + meal + buffer rows.
- `km` and `min` populated for every transit row (any row where `route` is set).
- `cost_local` populated where there is a real cost; `0` for free entries; `null` for placeholder rows.
- Day 1 (arrival) and last day (departure) include airport buffer rows matching airline recommendation — typically 2hr domestic, 3hr international.
- Active-hour budget: total per day from first activity start to last activity end is 14 hours maximum.
- See [`references/variant_transforms.md`](../variant_transforms.md) for v1 rules (this is the headline-packed track).

## Reference snippet

```json
{
  "itinerary": {
    "v1_standard": [
      {
        "day_label": "Day 1 — Arrival + Beach Sunset",
        "rows": [
          {"time": "08:30", "activity": "Cebu Pacific 5J 3010 MNL→DAD", "route": "Manila → Da Nang", "km": null, "min": 195, "cost_local": null, "sgd": null, "notes": "Check-in closes 60min before", "place_key": null},
          {"time": "11:45", "activity": "Land DAD; SIM + cash + Grab to hotel", "route": "DAD → My Khe", "km": 4.5, "min": 18, "cost_local": 110000, "sgd": null, "notes": "Grab pool ~₫110k; SIM at airport 7-Eleven", "place_key": null},
          {"time": "13:00", "activity": "Hotel check-in + light lunch", "route": null, "km": null, "min": null, "cost_local": 200000, "sgd": null, "notes": null, "place_key": null},
          {"time": "15:00", "activity": "My Khe Beach swim + rest", "route": null, "km": 0.2, "min": 3, "cost_local": 0, "sgd": null, "notes": "Flag system: green = safe, yellow = caution", "place_key": "my_khe_beach"},
          {"time": "17:30", "activity": "Sunset at Linh Ung Pagoda (Son Tra)", "route": "My Khe → Son Tra", "km": 8.0, "min": 22, "cost_local": 200000, "sgd": null, "notes": "Grab ~₫200k return; dress code — shoulders + knees covered", "place_key": "linh_ung_pagoda"},
          {"time": "19:30", "activity": "Dinner — Bún Chả Cá Bà Phiến", "route": "Son Tra → Hai Chau", "km": 7.5, "min": 20, "cost_local": 80000, "sgd": null, "notes": "Lunch-only; order arrives fast — 10min queue max", "place_key": "bun_cha_ca"},
          {"time": "21:00", "activity": "Dragon Bridge fire/water show (Fri/Sat/Sun only)", "route": "Hai Chau → Han River", "km": 1.5, "min": 6, "cost_local": 0, "sgd": null, "notes": "Show runs 21:00 sharp; skip if mid-week", "place_key": "dragon_bridge"},
          {"time": "22:30", "activity": "Return to hotel + buffer", "route": "Han River → My Khe", "km": 4.0, "min": 12, "cost_local": 80000, "sgd": null, "notes": null, "place_key": null}
        ]
      }
    ]
  }
}
```

## When done, run

```
python .claude/skills/itinerary-builder/scripts/synthesize.py --slug <slug> --stage 4
```

If errors: read them, patch `data.json`, re-run the same stage.
