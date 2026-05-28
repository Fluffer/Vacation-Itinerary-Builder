# Workflow — Full Pipeline

## Phase 0 — Intake Gate (BLOCKING)

See [`intake.md`](intake.md) for full rules.

Before any other phase, verify THREE required inputs:
1. **Destination** — country / city / area
2. **Dates + duration** — start date OR window AND nights/days
3. **Traveler nationality** — passport country (always ask, never assume)

If any missing → call AskUserQuestion → wait. Do NOT proceed to Phase 1.

If user provided a source doc, parse it AFTER intake completion (the doc may already supply some of the three — but always verify nationality explicitly).

## Phase 1 — Author data.json

Two paths. Both end with a fully-populated `trips/<slug>/data.json` conforming to [`../templates/trip_data.schema.json`](../templates/trip_data.schema.json).

**Path A — Source doc supplied:**
1. **Verify source doc** exists and readable. Convert .doc → .docx via LibreOffice if needed.
2. **Extract text** via `python-docx` paragraph iteration. Preserve heading levels.
3. **Extract tables** if any (some sources embed prices/schedules in tables).
4. **Map** extracted content into the JSON schema. Fill schema gaps from Claude knowledge + Web search.

**Path B — No source doc (compose from knowledge):**

There is **no automated synthesizer**. Claude composes `data.json` by hand, drawing on:
- Training knowledge for stable facts (geography, historical sites, classic restaurants)
- `WebSearch` / `WebFetch` for time-sensitive facts (visa rules, current prices, weather, scheduled events)
- The reference example `trips/da-nang/data.json` as a structural template

Target scope per destination (5-day trip):
- 15–25 `places[]` entries (iconic + hidden_gem + food + spa + nightlife)
- 4–7 `hotels[]`
- 4–6 `activity_pricing[]` pick-one bundles
- Full v1 + v2 + v3 itineraries with per-row time, route, km, min, cost_local, notes
- `risk_flags`, `booking_timeline`, `practical_info`, `checklist`, `hidden_gems_categorized`, `v1_v2_compare`, `weather_plan_b` (incl per_day_swaps + indoor_bank + booking_flex_tips), `distance_matrix`

Expect 800–1500 lines for a 5-day trip. Budget the time accordingly — Claude takes 5–15 minutes of focused authoring to compose a quality data.json. **Do not promise instant turn-around.**

**In both paths:**
1. **Detect language** of place names (Vietnamese, Thai, Japanese diacritics common). Store both native + ASCII fallback for image search.
2. **Re-confirm metadata** populated — pax count, base hotel area, airline if known.
3. **Validate via build_workbook.py date guard** before fetching images — fail fast on schema gaps.

## Phase 2 — Fact Validation (with timeout/fallback)

For each high-stakes claim, send to Ollama `second_opinion`:
- **Visa rule** for the traveler's passport + destination (number of days, e-visa requirement)
- **Currency rate** (recheck against XE / OANDA at build time)
- **Power plug type** for destination
- **Weather profile** for travel dates
- **Bridge/event schedules** that are time-locked (e.g. Dragon Bridge Fri/Sat/Sun)
- **Airport buffer** for the operating airline at the destination airport
- **Major attraction pricing** (current vs draft-stated)

Implementation in `scripts/validate_facts.py`:
- 60-second per-call timeout
- Try `deepseek-pro` → `deepseek-flash` → `glm` → `minimax` in order
- On every timeout/error, log to `trips/<slug>/unvalidated.md` and continue
- Final fallback: rule-based check against `references/known_facts.md` if maintained

## Phase 3 — Enhancement Rules

Apply rules from [`enhancement_rules.md`](enhancement_rules.md) to the parsed itinerary:
- Single-hotel base if trip ≤ 7 days
- Add distance + travel-time columns to every itinerary row
- Verify airport buffer ≥ airline recommendation
- Convert per-line transport+ticket into pick-ONE-bundle rows (see [`pricing_pattern.md`](pricing_pattern.md))
- Flag risk-heavy combinations (full-day outdoor + late nightlife = fatigue risk)

## Phase 4 — Variant Generation

See [`variant_transforms.md`](variant_transforms.md). Three variants by default:
- **v1 standard** — source doc enhanced; original places kept; corrections applied
- **v2 relaxed less-touristy** — apply substitution table; lift starts by 30–60 min; cap active hours per day
- **v3 bad-weather Plan B** — emitted only if destination + dates intersect monsoon/typhoon window

## Phase 5 — Hidden Gems & Comparison

Pull 20–30 alternative POIs from local-knowledge sources (Wikivoyage, local tourism boards). Group by category: nature, beaches, food, coffee, culture, wellness. Score each on tourist-density (low/med/high) and include in workbook Sheet 10.

## Phase 6 — Image & Map Assets

1. Fetch a hero photo for every named POI (Phase 1 extraction) — see [`image_sourcing.md`](image_sourcing.md)
2. Normalise every fetched image via PIL (`scripts/normalize_images.py`) — python-docx is strict about JPEG markers
3. Render two maps via `scripts/build_map.py`:
   - **Regional** at zoom 10 — day-trip targets
   - **City close-up** at zoom 12 — local sights
4. Labels positioned via NE/NW/SE/SW/E/W/N/S + extended NEE/SEE/NWW/SWW offsets when crowded

## Phase 7 — Workbook Assembly

`scripts/build_workbook.py` reads `trips/<slug>/data.json` and emits sheets per [`sheet_schemas.md`](sheet_schemas.md).

**Critical:**
- Use Arial font everywhere
- All amounts in VND-equivalent local currency; SGD/USD via formula referencing rate cell ($B$3 on Budget sheet)
- Day-total formulas via `SUM(start:end)` not hard-coded
- Bundle pricing rows: include a 5-cell warning at top of sheet — "DO NOT sum across paths"

## Phase 8 — Word Doc Assembly

`scripts/build_docx.py` reads same JSON + image dir. Structure:
1. Title page with hero photo
2. Regional map + city close-up map
3. Iconic sights (one entry per major POI: heading + photo + description + hyperlinks)
4. Hidden gems
5. Food
6. Spas
7. Nightlife
8. Accommodation
9. Practical links (booking, government, weather, tourism, apps)

Every entry has Google Maps + Wikipedia + official site hyperlinks where available.

## Phase 9 — Verification

1. Workbook: verify formulas via `recalc.py` if LibreOffice available, OR by loading via openpyxl and inspecting formula strings
2. Word doc: ensure no UnrecognizedImageError by re-saving each image via PIL beforehand
3. Open both in target apps (Excel + Word) — sanity check on Windows requires manual look

## Phase 10 — Delivery

Output to:
- `trips/<slug>/<slug>_Booking_Strategy.xlsx`
- `trips/<slug>/<slug>_Trip_Guide.docx`
- Copy to user `Downloads/` for convenience
- Print clickable file:// links in response

Report any `unvalidated.md` items at the end of the response so user knows what to verify manually.
