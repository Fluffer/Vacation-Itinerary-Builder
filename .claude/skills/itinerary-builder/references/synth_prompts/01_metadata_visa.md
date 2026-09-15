# Stage 1 — Metadata + Visa

> **Read first:** [`references/learnings.md`](../learnings.md) (curated lessons from prior runs)

## Inputs from prior stages
None — stage 1 starts fresh.

## What to produce in this stage
Fill the top-level `slug` field, the `metadata{}` block, and the `visa{}` block in `trips/<slug>/data.json`. The metadata block captures trip logistics (dates, origin, destination, passport, party size, hotel area, currency) and destination context (FX rate, climate, plug type, weather risk, water safety, tipping norms, emergency numbers). The visa block captures entry rules specific to the traveler's passport (rule description, days allowed, e-visa requirement, passport validity threshold, onward ticket requirement, and source URL). All fields in both blocks must be populated before advancing to stage 2.

## Schema fields to fill
- `slug` (string, e.g. `da-nang`)
- `metadata.dates_start` (ISO YYYY-MM-DD)
- `metadata.dates_end` (ISO YYYY-MM-DD)
- `metadata.origin` (departure city)
- `metadata.destination` (city/area)
- `metadata.passport` (issuing country code, e.g. `PH`)
- `metadata.pax` (integer)
- `metadata.base_hotel_area`
- `metadata.currency_code` (ISO 4217, e.g. `VND`)
- `metadata.fx_rate_to_sgd` (number — local units per 1 SGD)
- `metadata.fx_rate_anchor_date` (today)
- `metadata.climate_summary` (1 sentence)
- `metadata.power_plug` (e.g. `Type A/C`)
- `metadata.weather_risk` (enum: `low` / `medium` / `high`)
- `metadata.tap_water` (short string)
- `metadata.tipping` (short string)
- `metadata.emergency` (short string)
- `visa.rule` (string)
- `visa.days_allowed` (integer)
- `visa.e_visa_required` (bool)
- `visa.passport_validity_required_until` (ISO date)
- `visa.onward_ticket_required` (bool)
- `visa.source` (URL)

## Quality bar
- Visa rule MUST be passport-specific. Cite source URL (gov / IATA Travel Centre).
- FX rate expressed as local units per 1 SGD with anchor date (today's date by default). Recheck XE / OANDA.
- Climate summary uses destination + dates window (e.g. "Da Nang, mid-Aug -> hot 32 C, humidity 80%, typhoon-season-early, brief PM showers daily").
- `weather_risk` must be one of the three enum values: `low` / `medium` / `high`.
- `power_plug` must reflect the destination's standard. If it differs from the traveler's origin, surface it as a checklist item in a later stage.
- `emergency` includes local police and ambulance numbers at minimum.

## Reference snippet
```json
{
  "slug": "da-nang",
  "metadata": {
    "dates_start": "2026-08-14",
    "dates_end": "2026-08-18",
    "origin": "Manila",
    "destination": "Da Nang",
    "passport": "PH",
    "pax": 2,
    "base_hotel_area": "My Khe Beach",
    "currency_code": "VND",
    "fx_rate_to_sgd": 18500,
    "fx_rate_anchor_date": "2026-05-29",
    "climate_summary": "Hot humid 32C, brief PM showers, early typhoon season",
    "power_plug": "Type A/C",
    "weather_risk": "medium",
    "tap_water": "Not potable — bottled only",
    "tipping": "5-10% appreciated",
    "emergency": "113 police, 115 ambulance"
  },
  "visa": {
    "rule": "Visa-exempt 21 days (PH-VN bilateral)",
    "days_allowed": 21,
    "e_visa_required": false,
    "passport_validity_required_until": "2027-02-14",
    "onward_ticket_required": true,
    "source": "https://vietnam.travel/visa"
  }
}
```

## When done, run
```text
python .claude/skills/itinerary-builder/scripts/synthesize.py --slug <slug> --stage 1
```

If any errors: read them, patch data.json, re-run the same stage.
