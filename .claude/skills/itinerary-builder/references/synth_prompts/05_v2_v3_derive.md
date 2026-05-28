# Stage 5 — v2 Relaxed + v3 Weather (derived from v1)

> **Read first:** [`references/learnings.md`](../learnings.md)

## Inputs from prior stages
Stages 1-4 complete; v1_standard itinerary populated.

## What to produce
Fill `itinerary.v2_relaxed[]` and `itinerary.v3_weather[]` in `trips/<slug>/data.json`. Both arrays share the same row schema as `v1_standard`. For v2, apply the substitution table in `references/variant_transforms.md`: swap crowded headline sights for quieter alternatives drawn from `places[]` where `category=hidden_gem`, cap active hours at 11-12 per day (vs v1's 13-14), and insert rest blocks. For v3, replace outdoor + weather-sensitive rows with indoor alternatives drawn from `places[]` where `indoor=true` — treat every day as an all-day rain scenario; the decision tree and per-day swap matrix appear in stage 6. Both variants keep the same `day_label` strings as v1 so downstream compare sheets line up correctly.

## Schema fields to fill
- `itinerary.v2_relaxed[]` — same row shape as `v1_standard`
  - `day_label` — string, identical to v1 (no suffix)
  - `rows[].time` — HH:MM string
  - `rows[].activity` — string
  - `rows[].route` — string or null
  - `rows[].km` — number or null
  - `rows[].min` — integer or null
  - `rows[].cost_local` — integer or null
  - `rows[].sgd` — number or null
  - `rows[].notes` — string or null
  - `rows[].place_key` — string or null (must match a key in `places[]`)
- `itinerary.v3_weather[]` — same row shape as `v1_standard`
  - `day_label` — string, v1 label with `" (rain plan)"` appended
  - `rows[]` — same fields as v2 above

## Quality bar
- v2 has the SAME day count as v1. The stage 5 validator enforces this.
- v2 swaps headline crowded sights for `places[]` entries with `category=hidden_gem` where available; if no hidden-gem alternative exists, keep the original sight and add a `notes` value of `"Go early (before 08:30) or after 17:00 to avoid crowds"`.
- v2 active hours per day must not exceed 11-12 (count time from first non-transit row to last row). Enforce with rest blocks (`cost_local: 0`, no `place_key`).
- v2 keeps the SAME `day_label` strings as v1 — no suffix, no modification.
- v3 has the SAME day count as v1.
- v3 swaps every outdoor, weather-sensitive row for an indoor alternative from `places[]` (`indoor=true`). Eligible indoor categories: malls, museums, spas, cafes, indoor markets, food halls, covered temples. Transport-only rows (flights, airport transfers) are not swapped — they are reproduced as-is.
- v3 `day_label` strings are the v1 label with `" (rain plan)"` appended (e.g. `"Day 1 — Arrival (rain plan)"`).
- Both v2 and v3 use the identical row schema as v1: `time`, `activity`, `route`, `km`, `min`, `cost_local`, `sgd`, `notes`, `place_key`. No extra fields; no missing required fields.
- All `cost_local` amounts use the currency declared in `metadata.currency_code`.

## Reference snippets

```json
{
  "itinerary": {
    "v2_relaxed": [
      {
        "day_label": "Day 1 — Arrival + Beach Sunset",
        "rows": [
          {"time": "08:30", "activity": "Cebu Pacific 5J 3010 MNL→DAD", "route": "Manila → Da Nang", "km": null, "min": 195, "cost_local": null, "sgd": null, "notes": null, "place_key": null},
          {"time": "12:00", "activity": "Land DAD; SIM + cash + Grab to hotel (no rush)", "route": "DAD → My Khe", "km": 4.5, "min": 18, "cost_local": 110000, "sgd": null, "notes": null, "place_key": null},
          {"time": "13:30", "activity": "Hotel check-in, slow lunch at hotel", "route": null, "km": null, "min": null, "cost_local": 280000, "sgd": null, "notes": null, "place_key": null},
          {"time": "15:30", "activity": "Rest block — pool or nap", "route": null, "km": null, "min": null, "cost_local": 0, "sgd": null, "notes": "Recovery from early flight", "place_key": null},
          {"time": "17:30", "activity": "Sunset at quieter Lang Co Beach (skip touristy Linh Ung crowds)", "route": "My Khe → Lang Co", "km": 32, "min": 45, "cost_local": 250000, "sgd": null, "notes": null, "place_key": "lang_co_beach"},
          {"time": "19:30", "activity": "Dinner — Bún Chả Cá Bà Phiến (still open late)", "route": "Lang Co → Hai Chau", "km": 28, "min": 38, "cost_local": 80000, "sgd": null, "notes": null, "place_key": "bun_cha_ca"},
          {"time": "21:30", "activity": "Return + early bed", "route": "Hai Chau → My Khe", "km": 4.0, "min": 12, "cost_local": 80000, "sgd": null, "notes": null, "place_key": null}
        ]
      }
    ],
    "v3_weather": [
      {
        "day_label": "Day 1 — Arrival (rain plan)",
        "rows": [
          {"time": "08:30", "activity": "Cebu Pacific 5J 3010 MNL→DAD", "route": "Manila → Da Nang", "km": null, "min": 195, "cost_local": null, "sgd": null, "notes": null, "place_key": null},
          {"time": "11:45", "activity": "Land DAD; SIM + cash + Grab to hotel", "route": "DAD → My Khe", "km": 4.5, "min": 18, "cost_local": 110000, "sgd": null, "notes": null, "place_key": null},
          {"time": "13:00", "activity": "Hotel check-in + lunch", "route": null, "km": null, "min": null, "cost_local": 250000, "sgd": null, "notes": null, "place_key": null},
          {"time": "15:00", "activity": "Da Nang Museum of Cham Sculpture (indoor refuge)", "route": "My Khe → Hai Chau", "km": 4.5, "min": 14, "cost_local": 60000, "sgd": null, "notes": null, "place_key": "cham_museum"},
          {"time": "17:00", "activity": "Indochina Riverside Mall (browse, coffee)", "route": "Cham → Han River", "km": 0.8, "min": 4, "cost_local": 100000, "sgd": null, "notes": null, "place_key": "indochina_mall"},
          {"time": "19:00", "activity": "Dinner — Bún Chả Cá Bà Phiến (covered courtyard)", "route": "Han River → Hai Chau", "km": 1.0, "min": 4, "cost_local": 80000, "sgd": null, "notes": null, "place_key": "bun_cha_ca"},
          {"time": "20:30", "activity": "Return to hotel — rest", "route": "Hai Chau → My Khe", "km": 4.0, "min": 12, "cost_local": 80000, "sgd": null, "notes": null, "place_key": null}
        ]
      }
    ]
  }
}
```

## When done, run
```
python .claude/skills/itinerary-builder/scripts/synthesize.py --slug <slug> --stage 5
```

If any errors: read them, patch `trips/<slug>/data.json`, re-run the same stage.
