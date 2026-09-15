---
name: itinerary-builder
description: Plan a trip end-to-end: a multi-sheet Excel workbook (v1 packed / v2 relaxed / v3 bad-weather itineraries, pricing, budget) plus an illustrated Word guide with photos and maps. Use when asked to plan, build, enhance, or structure a trip — e.g. "plan a trip to X", "build an itinerary for X", "itinerary with a bad-weather plan", "5 days in [place]". Claude authors trips/<slug>/data.json from destination + dates + nationality; the Python pipeline renders the deliverables.
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

Three inputs minimum: **destination**, **dates + duration**, **traveler nationality**
(always ask — it drives visa rules; never assume). If any is missing or ambiguous,
call AskUserQuestion before doing any work. Optional: origin/airline, pax count,
source doc, pace preference.

See [`references/intake.md`](references/intake.md) for the per-field rules and the
AskUserQuestion template.

## Three-level variant guarantee

Every itinerary ships THREE pace variants, built whether or not the source
mentions them: **v1** packed tourist, **v2** relaxed less-touristy, **v3**
bad-weather fallback (**always emitted** — arid destinations get heat/dust
refuges, and the season only picks the decision-tree profile).
See [`references/variant_transforms.md`](references/variant_transforms.md).

## Dependencies

Python 3.10+ with `python-docx` (Word), `openpyxl` (Excel), `Pillow` (image
normalisation + map labels), `staticmap` (OSM tiles), plus `jsonschema`,
`requests`, `pytest`. Install: `pip install -r requirements.txt`.

The skill auto-loads from `.claude/skills/itinerary-builder/` (project) or
`~/.claude/skills/itinerary-builder/` (global). `trips/` always lives at the CWD
where you run the scripts, so the skill stays portable across projects.

## Workflow

Detailed step-by-step in [`references/workflow.md`](references/workflow.md). Summary:

0. **INTAKE GATE** — verify destination + dates/duration + nationality. If ANY missing, call AskUserQuestion. Do not proceed until all three are captured. See [`references/intake.md`](references/intake.md).
1. **Author data.json** at `trips/<slug>/data.json` conforming to [`templates/trip_data.schema.json`](templates/trip_data.schema.json). Two paths:
   - **Parse a source doc** (user-supplied .docx draft) — extract places, times, prices.
   - **Compose via staged synthesizer** — when no source doc, Claude uses the staged synth_prompts at `references/synth_prompts/0N_*.md`. Six stages: metadata+visa → places → hotels+pricing+budget → v1 itinerary → v2+v3 derive → ancillary. After each stage write data.json and run `python <SKILL_DIR>/scripts/synthesize.py --slug <slug> --stage N` to validate. Validator output guides revisions. `--stage final` runs the strict schema check and writes the fact-validate checklist. See [`references/workflow.md`](references/workflow.md) Phase 1 and [`references/learnings.md`](references/learnings.md).
2. **Fact-validate** key claims (visa for the SPECIFIC nationality, weather for dates, pricing, schedules). `scripts/validate_facts.py` writes `validate_prompts.md` + `unvalidated.md`; Claude then runs each prompt through the MCP `second_opinion` tools (60-second per-call timeout, cascade deepseek-pro → deepseek-flash → glm → minimax). Never stall the pipeline on a timeout.
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
7. **Build workbook** via `<SKILL_DIR>/scripts/build_workbook.py` — sets `fullCalcOnLoad` so Excel recalculates on open
8. **Build Word doc** via `<SKILL_DIR>/scripts/build_docx.py` — embeds photos, maps, hyperlinks
9. **Verify** outputs open without error; report file paths to user

## Output locations

Trips workspace is `{CWD}/trips/<slug>/` — project-relative, not the skill install
location, so the skill is portable. Override with `ITINERARY_TRIPS_ROOT=/some/path`.
It holds `data.json`, `images/`, `<slug>_Booking_Strategy.xlsx`, and
`<slug>_Trip_Guide.docx` (also copied to `Downloads/` with `--downloads-copy`).

## Sheet count is data-driven

The 14-sheet structure shipped for Da Nang is NOT hardcoded. Sheets are emitted conditionally:
- v1 Daily Itinerary, v2 Relaxed, v3 Bad-Weather — **all three always emitted** (the skill's core promise)
- Hidden Gems only if trip-data lists alternative POIs (auto-generated if missing)
- Distance Matrix always emitted
- Activity Pricing always emitted when bundleable activities exist

See [`references/sheet_schemas.md`](references/sheet_schemas.md) for full list and conditions.

## Fact-validation fallback strategy

`scripts/validate_facts.py` cannot call models itself (MCP tools only exist inside
Claude); it writes the checklist and the pending list. Claude performs the calls.
If validation hangs or errors:
1. Leave that fact in `trips/<slug>/unvalidated.md`
2. Add a yellow ⚠️ flag to the corresponding cell / paragraph in output
3. Continue the pipeline — never block deliverables on validation
4. Try models in order: `deepseek-pro` → `deepseek-flash` → `glm` → `minimax` → rule-based

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
