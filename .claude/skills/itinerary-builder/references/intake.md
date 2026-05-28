# Intake Gate — Required Inputs

Before any pipeline work, capture THREE mandatory inputs. If ANY missing or ambiguous, call `AskUserQuestion` and wait.

## The three required inputs

### 1. Destination (where)

Accept any of:
- Country (`Vietnam`, `Japan`, `Iceland`)
- City (`Tokyo`, `Lisbon`, `Da Nang`)
- Area / region (`central Vietnam`, `Hokkaido`, `Faroe Islands`, `Tuscany`)
- Multi-stop (`Bangkok + Chiang Mai`)

**If too broad to anchor a base hotel** (e.g. user says "Vietnam" or "Japan"), ask for sub-region.

Examples:
- "Vietnam" → ask: Hanoi+Halong / Da Nang+Hoi An / Saigon+Mekong / other
- "Japan" → ask: Tokyo / Kyoto+Osaka / Hokkaido / Okinawa / multi-city
- "Bali" → ask: Seminyak / Ubud / Canggu / Uluwatu / mix

### 2. Dates AND duration (when + how long)

Need BOTH halves:
- **Start date** — specific (`Aug 14 2026`) OR a window (`late October 2026`, `mid-Q2 2026`)
- **Duration** — nights or days (`5 days`, `1 week`, `10 nights`)

Common patterns:
- User gives `"Aug 14–18, 2026"` → both present, derive duration as 4 nights/5 days
- User gives `"5 days in August"` → ask for specific start date OR resolve to "best week for weather"
- User gives `"sometime next year"` → ask for season + duration

### 3. Traveler nationality / passport (who)

**ALWAYS ASK. Never assume.** Critical for visa rules.

Single-pax case: capture the one passport.

Multi-pax mixed-passport case: capture all unique nationalities. Visa block in workbook lists rules per nationality.

Common passports (offer as quick-pick options when relevant):
- Singapore (SG) — strong visa-free access
- Philippines (PH) — ASEAN bilaterals, often 21–30 days
- USA / Canada — e-visa common
- UK / EU — Schengen-or-equivalent
- Australia / NZ
- China / India — more restrictive

### Optional but useful (ask at most once each)

- **Origin city + airline** — needed for flight booking timeline + airport buffer rule. If unknown, default to "flexible" and skip booking-timeline column for flights.
- **Pax count** — default 2 if user uses "we"; default 1 if "I". Confirm if ambiguous.
- **Pace preference** — usually skipped; all 3 variants generated regardless.
- **Source draft document** — if user references one ("enhance this"), get path.

## Question phrasing — AskUserQuestion call

Use ONE AskUserQuestion call with up to 4 questions. Combine missing fields. Example for blank-slate "plan a trip":

```
[
  {
    "question": "Where do you want to go?",
    "header": "Destination",
    "options": [...sensible defaults if hint present...]
  },
  {
    "question": "When and for how long?",
    "header": "Dates",
    "options": [
      {"label": "Specific dates (I'll type them)", "description": "..."},
      {"label": "Flexible — I want best weather window", "description": "..."},
      {"label": "Long weekend (3–4 days)", "description": "..."},
      {"label": "Week-long (5–7 days)", "description": "..."}
    ]
  },
  {
    "question": "Whose passport(s) will be traveling?",
    "header": "Passport",
    "multiSelect": true,
    "options": [
      {"label": "Singapore (SG)"},
      {"label": "Philippines (PH)"},
      {"label": "USA / Canada"},
      {"label": "UK / EU"}
    ]
  }
]
```

## After intake — derive remaining fields

Once destination + dates + nationality captured, derive:
- `slug` — short identifier `<destination>-<year>` (e.g. `tokyo-2026`)
- `weather_risk` — lookup destination + month in Köppen + storm-basin data
- `currency_code`, `power_plug`, `language` — destination defaults
- `base_hotel_area` — propose a default for the destination, ask confirm if unsure
- `fx_rate_to_sgd` — current rate (validate via Ollama or fixed lookup)

Write all to `trips/<slug>/data.json` `metadata` block before continuing pipeline.

## Hard rule

**Do NOT call any build script until the intake gate is satisfied.** The pipeline assumes `metadata.passport`, `metadata.dates_start`, `metadata.dates_end`, `metadata.destination` are all populated. Missing fields = silent bad output.
