# Stage 6 — Ancillary blocks (final)

> **Read first:** [`references/learnings.md`](../learnings.md)

## Inputs from prior stages
Stages 1-5 complete.

## What to produce
Populate all remaining `data.json` blocks so the file passes strict schema validation (`partial=False`). The stage runner auto-derives `distance_matrix` from `places[].distance_km_from_base` and merges `weather_plan_b.indoor_bank` from `places[]` where `indoor=true`, so you do not need to provide those — focus on the fields listed below. Include `risk_flags`, booking logistics, practical travel info, packing checklist, hidden gems, v1/v2 comparison rows, and both map configs. Coordinates for map entries must come from `places[]` already populated in stage 2; do not invent new lat/lon values.

## Schema fields to fill
- `risk_flags[]` — array of `[label, note]` pairs surfaced on Overview sheet (2-5 trip-specific entries)
- `booking_timeline[]` — entries `{window, lead_time, action, why}` (5-10 entries, spanning `"12+ weeks"` through `"Day-of"`)
- `practical_info[]` — array of `[label, text]` pairs (10-20 entries)
- `checklist[]` — entries `{category, item}` (15-30 entries)
- `hidden_gems_categorized{}` — object keyed by category, each value a list of `{name, distance, travel_time, why_quiet, notes}` (at least 3 categories)
- `v1_v2_compare[]` — entries `{item, v1, v2, why}` aligned to substituted rows across v1 vs v2
- `weather_plan_b.emit` (bool)
- `weather_plan_b.rationale` (1 sentence describing destination climate + season)
- `weather_plan_b.decision_tree[]` — exactly 5 ordered severity bands, each `{condition, trigger, action}`. The condition/trigger labels adapt to the destination's `weather_risk` profile (rain/storm slots become extreme-heat / dust / wildfire for arid destinations).
- `weather_plan_b.per_day_swaps[]` — one entry per day `{day_label, swaps: [{original, why_risk, trigger, action, alt_local, channel}]}`
- `weather_plan_b.booking_flex_tips[]` — array of `{label, text}` objects (renderer requirement; a plain string array raises `AttributeError`)
- `weather_plan_b.indoor_bank[]` — **auto-merged** by stage runner from `places[]` where `indoor=true`; you may add extra entries not already in `places[]`
- `distance_matrix[]` — **auto-derived** from `places[].distance_km_from_base`; you may add extra point-to-point entries not already covered
- `maps.regional.zoom` — set to `10`
- `maps.regional.places[]` — each entry: `{lat, lon, label, color, pos}`
- `maps.city_closeup.zoom` — set to `12`
- `maps.city_closeup.places[]` — each entry: `{lat, lon, label, color, pos}`
- `transport_tips[]` — string array
- `accommodation_recommendation` — string
- `practical_links{}` — object keyed by category, each value an array of `{label, url}`

## Quality bar
- `booking_timeline[]` has 5-10 entries covering the window from `"12+ weeks"` through `"Day-of"`.
- `practical_info[]` has 10-20 `[label, text]` pairs covering: currency, payments, SIM/eSIM, transport, local manners, safety, drinking water, plug type, language, tipping.
- `checklist[]` has 15-30 entries grouped by category: Documents, Money, Health, Devices, Clothing, Day-Pack.
- `hidden_gems_categorized` has at least 3 categories (e.g. nature, food, culture); each place entry includes all five fields.
- `weather_plan_b.decision_tree` has exactly 5 ordered severity bands, each with `condition`, `trigger`, and `action` (labels vary by the destination's `weather_risk` profile — see `references/weather_pivot_pattern.md`).
- `weather_plan_b.per_day_swaps` has one entry per itinerary day, each with 1-3 swaps.
- `maps.regional` zoom=10; `maps.city_closeup` zoom=12. Each `.places[]` entry has `lat`, `lon`, `label`, `color`, `pos`.
  - `color` enum: `red`, `blue`, `orange`, `green`, `purple`, `darkblue`
  - `pos` enum: `NE`, `NW`, `SE`, `SW`, `E`, `W`, `N`, `S`, `NEE`, `SEE`, `NWW`, `SWW`
- Both maps must have at least 6 labelled places each. Use coordinates already present in `places[]` (set in stage 2).
- `risk_flags` calls out 2-5 trip-specific risks — e.g. `["Typhoon season early", "Watch landslip alerts for Hai Van Pass"]`.
- `v1_v2_compare[]` has one entry per substituted item; `item`, `v1`, and `v2` values align with the same rows in the v1 and v2 itineraries from stages 4-5.
- `booking_flex_tips` items are `{label, text}` objects (renderer requirement; schema is permissive but `build_workbook` expects dict items).

## Reference snippets

Embed these blocks verbatim (adapt values to the destination):

```json
{
  "booking_timeline": [
    {"window": "12+ weeks", "lead_time": "Now", "action": "Lock flights — cheapest fares 8-12 weeks out", "why": "Cebu Pacific / VietJet sales typically run 12 weeks before"},
    {"window": "8-10 weeks", "lead_time": "Soon", "action": "Reserve hotel (flexible rate)", "why": "Best inventory + free cancel up to 7 days before"},
    {"window": "4-6 weeks", "lead_time": "Soon", "action": "Book day-tour bundles via Klook", "why": "Klook drip-discount best in this window"},
    {"window": "2-3 weeks", "lead_time": "Soon", "action": "Confirm visa-exempt status not changed (PH-VN bilateral)", "why": "Bilateral agreements can change without much notice"},
    {"window": "1 week", "lead_time": "Now", "action": "Buy eSIM (Airalo / Klook) + travel insurance", "why": "eSIM activatable on arrival; insurance must precede travel"},
    {"window": "Day before", "lead_time": "Now", "action": "Check Dragon Bridge show calendar (Fri/Sat/Sun 21:00)", "why": "Don't miss the show if schedule allows"},
    {"window": "Day-of", "lead_time": "Now", "action": "Confirm typhoon / weather check; pre-book Grab from DAD if possible", "why": "August is early typhoon season"}
  ],
  "weather_plan_b": {
    "emit": true,
    "rationale": "Da Nang mid-August: 32C humid, brief PM showers daily, early typhoon season",
    "decision_tree": [
      {"condition": "clear", "trigger": "No rain in AM/PM forecast", "action": "Proceed with v1 (or v2 if pace preferred)"},
      {"condition": "PM showers", "trigger": "Showers forecast after 13:00", "action": "Front-load outdoor for morning; move museum/mall to PM"},
      {"condition": "all-day rain", "trigger": "Rain probability >70% all day", "action": "Switch to v3 weather plan; indoor-only day"},
      {"condition": "tropical storm warning", "trigger": "Met service storm warning issued", "action": "Stay in district; cafes + mall + spa loop; skip beaches"},
      {"condition": "typhoon warning", "trigger": "Typhoon signal issued", "action": "Indoor hotel day; check airline rebook policy; postpone outdoor tours by >= 1 day"}
    ],
    "per_day_swaps": [
      {
        "day_label": "Day 1 — Arrival",
        "swaps": [
          {"original": "My Khe Beach swim", "why_risk": "Outdoor + rain risk", "trigger": "PM showers or worse", "action": "Replace with Da Nang Museum of Cham Sculpture (indoor)", "alt_local": 60000, "channel": "DIY"}
        ]
      }
    ],
    "booking_flex_tips": [
      {"label": "Hotel cancellation", "text": "Choose hotel with free-cancel window of 24h"},
      {"label": "Flight fare class", "text": "Cebu Pacific Lite fares non-changeable — buy Plus if typhoon risk high"},
      {"label": "Tour refund window", "text": "Klook tours typically refundable up to 48h before"}
    ]
  }
}
```

## When done, run

```text
python .claude/skills/itinerary-builder/scripts/synthesize.py --slug <slug> --stage 6
```

Stage 6 runs STRICT schema (`partial=False`) — all required top-level blocks must be present.

If any errors: read them, patch `trips/<slug>/data.json`, re-run stage 6 until clean.
