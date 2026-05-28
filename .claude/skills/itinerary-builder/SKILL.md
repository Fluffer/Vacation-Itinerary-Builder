---
name: itinerary-builder
description: Render a 14-sheet Excel workbook + illustrated Word guide from a structured trips/<slug>/data.json (overview · booking timeline · v1/v2/v3 pace variants adjacent · v1-vs-v2 compare · accommodation · food/spa/nightlife · hidden-gems · activity pricing · distance matrix · budget · practical info · checklist). Workbook also pulls Wikipedia photos + 2 labelled OpenStreetMap maps for the Word guide. Claude authors data.json from destination + dates + nationality using local + web knowledge; the Python pipeline then renders the deliverables. Invoke when user asks to plan / build / enhance a trip and is willing to wait while Claude composes the data file. Trigger phrases: "plan a trip to X", "build itinerary for X", "make a travel plan", "enhance this trip plan", "structured trip plan", "trip package with alternatives", "itinerary with bad weather plan", "trip word doc with maps", "5 days in [place]".
---

# Itinerary Builder

Builds a complete 3-level travel-planning package for any destination:
1. **Excel workbook** — multi-sheet planning model with all 3 pace variants, pricing, distances, budget formulas
2. **Word document** — illustrated visual guide with embedded photos, hyperlinks, and labelled maps

## When to invoke

Any request to plan, build, enhance, or structure a trip. Examples:
- "Plan me 5 days in Tokyo"
- "Build an itinerary for Bali Aug 14–18"
- "Enhance this draft trip plan: [docx]"
- "Make a 3-level itinerary for Lisbon"
- "Trip package for Hanoi, late October, with bad-weather alternatives"

**Important — set expectations:** With no source doc, Claude composes data.json by hand (training + Web). This takes 5–15 min of focused authoring before the Python pipeline renders the workbook + doc. Tell the user up-front. If they want sub-minute turn-around, ask them to supply a draft doc first.

## Required inputs — MUST ASK if missing

The skill needs THREE inputs minimum. If ANY is missing or ambiguous, **ask the user before doing any work** — use the AskUserQuestion tool with one question per missing field.

### 1. Destination (country / city / area)
- Accept loose forms: "Tokyo", "central Vietnam", "Bali", "Faroe Islands", "Sicily"
- Resolve to a base hotel area if possible (e.g. "Bali" → ask which area: Seminyak / Ubud / Canggu)

### 2. Dates AND duration
Need BOTH:
- **Start date** (specific, e.g. "Aug 14 2026") OR a window ("late October", "mid-2026")
- **Duration** in nights/days (e.g. "5 days / 4 nights")

If user gives only one, ask for the other.

### 3. Traveler nationality (passport country) — ALWAYS ASK
Drives visa lookup. Different passports → different rules → different documents required. Never assume.
- If multi-pax with mixed nationalities, capture all and validate each.

### Optional but recommended (ask once if not obvious)
- Origin city + airline (for flight buffer + booking timeline)
- Pax count (defaults to 1–2 if not stated)
- Source document if user has a draft
- Pace preference (offered automatically once known)

### Intake question template

Use AskUserQuestion with 1–3 questions max in one call. Example for blank-slate request "plan me a trip to Vietnam":

```
Q1: Where in Vietnam? (country is too broad to anchor a base hotel)
  - Da Nang / Hoi An (central)
  - Hanoi + Halong Bay (north)
  - Saigon + Mekong (south)
  - Other (let me specify)

Q2: When + how long?
  - (free-form: "Aug 14–18, 2026 / 5 days")

Q3: Whose passport?
  - Singapore (SG)
  - Philippines (PH)
  - USA / EU / Other
```

## Three-level variant guarantee

Every itinerary produced has THREE pace variants — built whether or not source mentions them:

### v1 — Normal Packed Tourist Schedule
Hits all the headline sights at reasonable pace. ~13–14 active hours/day. Suits first-time visitor.

### v2 — Relaxed Less-Touristy Schedule
Substitutes crowd-heavy headline sights with vetted quieter alternatives. Caps active hours at 11–12. Adds rest blocks. Sunrise shifts for popular attractions. Optional (not mandatory) nightlife. Suits leisure / couples / older travelers.

### v3 — Bad-Weather Fallback
Per-day swap matrix mapping outdoor items → indoor substitutes. 5-level forecast decision tree (clear / PM showers / all-day rain / tropical storm / typhoon warning). ALWAYS emitted (even for arid destinations — covers unexpected sandstorm / heat-wave indoor refuges).

See [`references/variant_transforms.md`](references/variant_transforms.md) for full transform rules.

## Workflow

Detailed step-by-step in [`references/workflow.md`](references/workflow.md). Summary:

0. **INTAKE GATE** — verify destination + dates/duration + nationality. If ANY missing, call AskUserQuestion. Do not proceed until all three are captured. See [`references/intake.md`](references/intake.md).
1. **Author data.json** at `trips/<slug>/data.json` conforming to [`templates/trip_data.schema.json`](templates/trip_data.schema.json). Two paths:
   - **Parse a source doc** (user-supplied .docx draft) — extract places, times, prices.
   - **Compose via staged synthesizer** — when no source doc, Claude uses the staged synth_prompts at `references/synth_prompts/0N_*.md`. Six stages: metadata+visa → places → hotels+pricing+budget → v1 itinerary → v2+v3 derive → ancillary. After each stage write data.json and run `python scripts/synthesize.py --slug <slug> --stage N` to validate. Validator output guides revisions. Final pass: `--stage final` runs strict schema + Ollama fact-validate (non-blocking). See [`references/workflow.md`](references/workflow.md) Phase 1 for the full flow and [`references/learnings.md`](references/learnings.md) for prior-run lessons that inform each stage.
2. **Fact-validate** key claims (visa for the SPECIFIC nationality, weather for dates, pricing, schedules) via Ollama models with 60-second per-call timeout; on timeout flag entry as `unvalidated` and proceed (do NOT stall the pipeline)
3. **Apply enhancement rules** (see [`references/enhancement_rules.md`](references/enhancement_rules.md)):
   - Single-hotel base unless trip ≥ 7 days
   - Add distance/time columns to every itinerary row
   - Convert per-line pricing into pick-ONE-bundle paths where vendor offers package deals
   - Verify airport buffer ≥ vendor recommendation
4. **Generate ALL THREE variants** per [`references/variant_transforms.md`](references/variant_transforms.md):
   - **v1 normal packed tourist** — full headline-sight schedule, ~13–14 active hr/day
   - **v2 relaxed less-touristy** — substitute crowded sights with vetted alternatives; cap 11–12 active hr; rest blocks; sunrise shifts
   - **v3 bad-weather fallback** — per-day indoor swaps + 5-level decision tree (clear → typhoon). ALWAYS emit — even arid destinations need heat-wave / sandstorm fallbacks.
5. **Fetch images** per [`references/image_sourcing.md`](references/image_sourcing.md) — Wikipedia REST summary + Wikimedia Commons search, normalised via PIL
6. **Render maps** per [`references/map_rendering.md`](references/map_rendering.md) — staticmap + PIL labels; produce regional + city close-up
7. **Build workbook** via `scripts/build_workbook.py` — recalculates formulas (or verifies on Windows)
8. **Build Word doc** via `scripts/build_docx.py` — embeds photos, maps, hyperlinks
9. **Verify** outputs open without error; report file paths to user

## Output locations

Trips workspace lives at `{CWD}/trips/<slug>/` — i.e. relative to the user's working directory, NOT the skill install location. This makes the skill portable: same skill produces outputs into whichever project is open. Override via env var `ITINERARY_TRIPS_ROOT=/some/path`.

- `{CWD}/trips/<slug>/data.json` — structured trip data
- `{CWD}/trips/<slug>/images/` — fetched + normalised photos + rendered maps
- `{CWD}/trips/<slug>/<slug>_Booking_Strategy.xlsx` — 14-sheet workbook
- `{CWD}/trips/<slug>/<slug>_Trip_Guide.docx` — illustrated guide
- ALSO copies into user `Downloads/` folder for convenience (via `--downloads-copy`)

## Sheet count is data-driven

The 14-sheet structure shipped for Da Nang is NOT hardcoded. Sheets are emitted conditionally:
- v1 Daily Itinerary, v2 Relaxed, v3 Bad-Weather — **all three always emitted** (the skill's core promise)
- Hidden Gems only if trip-data lists alternative POIs (auto-generated if missing)
- Distance Matrix always emitted
- Activity Pricing always emitted when bundleable activities exist

See [`references/sheet_schemas.md`](references/sheet_schemas.md) for full list and conditions.

## Ollama fallback strategy

If Ollama validation hangs or errors:
1. Skip that single fact, log to `trips/<slug>/unvalidated.md`
2. Add a yellow ⚠️ flag to the cell / paragraph in output
3. Continue pipeline — never block deliverables on validation
4. Try models in order: `deepseek-pro` → `deepseek-flash` → `glm` → `minimax` → rule-based

See `scripts/validate_facts.py` for implementation.

## Dependencies

Python 3.10+ with:
- `python-docx` (input parse + Word output)
- `openpyxl` (Excel)
- `Pillow` (image normalisation + map label overlay)
- `staticmap` (OSM tile-based map renderer)
- `urllib` (Wikipedia REST + image download — stdlib)

Install: `pip install python-docx openpyxl Pillow staticmap jsonschema requests pytest`

## Running the skill

Scripts live inside this skill at `.claude/skills/itinerary-builder/scripts/`. Reference them as `<SKILL_DIR>/scripts/<name>.py`. CWD should be the user's project root (where `trips/` lives or will be created).

```powershell
# Resolve the skill dir once
$SKILL = ".claude/skills/itinerary-builder"

# One-shot orchestrator (after data.json is in place)
python "$SKILL/scripts/run_all.py" --slug manila --downloads-copy
```

OR step-by-step (when iterating):
```powershell
python "$SKILL/scripts/fetch_images.py" --slug manila
python "$SKILL/scripts/normalize_images.py" --slug manila
python "$SKILL/scripts/build_map.py" --slug manila
python "$SKILL/scripts/build_workbook.py" --slug manila
python "$SKILL/scripts/build_docx.py" --slug manila
```

If running from a different project entirely, point at the trips workspace explicitly:

```powershell
$env:ITINERARY_TRIPS_ROOT = "D:\TravelPlans"
python "$SKILL/scripts/run_all.py" --slug bali-2026 --downloads-copy
```

## Installation footprint

```
<project>/
├── .claude/
│   └── skills/
│       └── itinerary-builder/        ← this skill (auto-discovered)
│           ├── SKILL.md
│           ├── references/
│           ├── scripts/
│           └── templates/
└── trips/                            ← user workspace (per-project)
    └── <slug>/
        ├── data.json
        ├── images/
        ├── <slug>_Booking_Strategy.xlsx
        └── <slug>_Trip_Guide.docx
```

To make the skill available globally (any project), install at `~/.claude/skills/itinerary-builder/` instead. Behaviour identical — `trips/` still lives at the CWD where you run the scripts.

## Reference docs (read these to customise)

- [`references/workflow.md`](references/workflow.md) — full pipeline walkthrough
- [`references/sheet_schemas.md`](references/sheet_schemas.md) — what goes in each sheet
- [`references/pricing_pattern.md`](references/pricing_pattern.md) — pick-ONE-bundle rule
- [`references/variant_transforms.md`](references/variant_transforms.md) — how v2/v3 differ from v1
- [`references/weather_pivot_pattern.md`](references/weather_pivot_pattern.md) — Plan B decision-tree template
- [`references/image_sourcing.md`](references/image_sourcing.md) — fetching royalty-free photos
- [`references/map_rendering.md`](references/map_rendering.md) — labelled-map technique
- [`references/enhancement_rules.md`](references/enhancement_rules.md) — what to auto-add/fix
- [`references/error_handling.md`](references/error_handling.md) — failure modes + fallbacks

## Example

Da Nang trip (Aug 14–18 2026) was used to develop this skill. Real output preserved at `trips/da-nang/` as a reference implementation.
