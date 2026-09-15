# Stage 3 — Hotels, Activity Pricing, Budget

> **Read first:** [`references/learnings.md`](../learnings.md)

## Inputs from prior stages
Stages 1 + 2 complete (metadata, visa, places).

## What to produce
Fill `hotels[]`, `activity_pricing[]`, and `budget{}` in `trips/<slug>/data.json`. Hotels provide accommodation options spanning tiers so the traveler can choose by spend level. Activity pricing lists per-category booking paths as pick-ONE options — do not sum paths; each path is a mutually exclusive channel for the same activity. Budget categories give daily or trip-total local-currency ranges for the main spend buckets, anchored by the FX rate in `metadata.fx_rate_to_sgd`. All amounts use the local currency declared in `metadata.currency_code`; field names use the `*_local` suffix.

## Schema fields to fill
- `hotels[].name`
- `hotels[].tier` — enum: `Budget`, `Mid`, `Luxury`, `Resort`
- `hotels[].rating` — string, e.g. `"4.0★"`
- `hotels[].sgd_low` — integer
- `hotels[].sgd_high` — integer
- `hotels[].notes` — 1 sentence max, concrete detail
- `hotels[].links[]` — array of `{label, url}`; empty array `[]` is acceptable
- `activity_pricing[].category`
- `activity_pricing[].paths[].name`
- `activity_pricing[].paths[].channel` — concrete platform or method (e.g. `"Klook"`, `"GetYourGuide"`, `"hotel concierge"`, `"Grab app"`, `"DIY"`)
- `activity_pricing[].paths[].local_per_pax` — integer, local currency
- `activity_pricing[].paths[].includes` — short string
- `activity_pricing[].extras[]` — optional array of add-on notes
- `budget.rate_local_per_sgd` — matches `metadata.fx_rate_to_sgd`
- `budget.categories[].category`
- `budget.categories[].low_local` — integer
- `budget.categories[].high_local` — integer
- `budget.flight_sgd_low` — integer
- `budget.flight_sgd_high` — integer
- `budget.hotel_sgd_low` — integer (lowest nightly rate across hotels[])
- `budget.hotel_sgd_high` — integer (highest nightly rate across hotels[])

## Quality bar
- Hotels cover tiers: at minimum 1 Budget, 1 Mid, 1 Luxury or Resort (4-7 entries total). SGD ranges must be realistic for destination + season — no `300-400 SGD/night` in a budget-destination, no `40-50 SGD/night` in Tokyo Ginza.
- `hotels[].notes` is 1 sentence, concrete: `"5min walk to beach"`, not `"great location"`.
- Activity pricing: each `category` has 2-3 `paths` representing distinct booking channels. Pick-ONE semantics apply — paths are mutually exclusive. Do not include warning text in the data; stage 6 sheet handles user messaging.
- Budget `categories[]` must include at minimum: food, local transport, attractions, sims/wifi, misc. Express food and transport as per-pax-per-day; express sims/wifi and misc as per-pax trip totals.
- `budget.rate_local_per_sgd` must match `metadata.fx_rate_to_sgd` exactly.
- All `*_local` amounts use the currency from `metadata.currency_code`.

## Reference snippets

```json
{
  "hotels": [
    {
      "name": "Belmont Hotel Manila",
      "tier": "Mid",
      "rating": "4.0★",
      "sgd_low": 95,
      "sgd_high": 130,
      "notes": "Inside NAIA T3 walking distance",
      "links": [{"label": "Booking.com", "url": "https://booking.com/example"}]
    },
    {
      "name": "Z Hostel Makati",
      "tier": "Budget",
      "rating": "3.5★",
      "sgd_low": 25,
      "sgd_high": 45,
      "notes": "Dorms + privates, rooftop bar",
      "links": []
    },
    {
      "name": "Shangri-La The Fort",
      "tier": "Luxury",
      "rating": "5.0★",
      "sgd_low": 280,
      "sgd_high": 450,
      "notes": "BGC, full resort facilities",
      "links": []
    }
  ],
  "activity_pricing": [
    {
      "category": "airport_transfer",
      "paths": [
        {"name": "Grab car DIY", "channel": "Grab app", "local_per_pax": 600, "includes": "30min ride to Makati"},
        {"name": "Hotel sedan", "channel": "hotel concierge", "local_per_pax": 1800, "includes": "Meet-and-greet, fixed fare"}
      ]
    },
    {
      "category": "intramuros_tour",
      "paths": [
        {"name": "Self-walk", "channel": "DIY", "local_per_pax": 75, "includes": "Fort Santiago entry only"},
        {"name": "Carlos Celdran-style walking tour", "channel": "Klook", "local_per_pax": 1800, "includes": "3hr guided + entry"}
      ]
    }
  ],
  "budget": {
    "rate_local_per_sgd": 42,
    "categories": [
      {"category": "Food (per pax/day)", "low_local": 1200, "high_local": 2800},
      {"category": "Local transport (per pax/day)", "low_local": 300, "high_local": 800},
      {"category": "Attractions (per pax total)", "low_local": 2000, "high_local": 6000},
      {"category": "SIM/eSIM (one-time)", "low_local": 350, "high_local": 800},
      {"category": "Tips + misc (per pax total)", "low_local": 800, "high_local": 2000}
    ],
    "flight_sgd_low": 180,
    "flight_sgd_high": 320,
    "hotel_sgd_low": 95,
    "hotel_sgd_high": 280
  }
}
```

## When done, run
```text
python .claude/skills/itinerary-builder/scripts/synthesize.py --slug <slug> --stage 3
```

If any errors: read them, patch `trips/<slug>/data.json`, re-run the same stage.
