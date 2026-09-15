# Variant Transforms — v1 → v2 → v3

Three itinerary variants are **always** generated. Skill's core promise — every output has all three. Each is a transform of v1 via a documented rule set.

## v1 — Normal Packed Tourist Schedule

The parsed source document, enhanced with:
- Distance + travel-time columns
- Pricing corrected for accuracy
- Bundle paths consolidated (see [`pricing_pattern.md`](pricing_pattern.md))
- Risk flags appended for any over-packed days
- Visa / weather / airport-buffer facts validated

## v2 — Relaxed Less-Touristy

Apply transforms in order:

### T1. Substitute headline tourist sites with vetted quieter alternatives

| If v1 includes | Swap to |
|---|---|
| Cable-car mountain resort (Ba Na, Genting) | Scenic coastal pass + quiet bay (Hai Van + Lăng Cô) |
| Old-town day + caves same day | Old-town ONLY w/ quiet-beach detour (e.g. An Bàng) |
| Crowded headline beach | Off-strip alternative (Nam Ô, secret cove) |
| Tour-bus seafood (Mộc Hải Sản) | Locals' seafood (Bé Mặn) |
| Iconic landmark cafe (Cộng) | Specialty roaster (43 Factory) |

Maintain destination-specific substitutions in `trips/<slug>/swaps.json`.

### T2. Time-shift to off-peak windows

- Move headline-attraction visits to **sunrise** (05:30) where possible — empty + photogenic + cooler
- Push lunch later (13:00–14:00) to skip tour-group lunch rush
- Build a 90–120 min hotel rest block into the afternoon

### T3. Cap active hours per day

| v1 | v2 |
|---|---|
| 13–14 active hours | 11–12 max |
| Mandatory pub crawl | Optional — only if energy permits |
| Two spa sessions (90 + 120) | One single 150-min long ritual |

### T4. Defer same-day combos

Any day combining 2+ outdoor anchors (Marble + Hoi An same day; Ba Na + nightlife same day) gets split. The dropped anchor moves to a free slot on another day.

### T5. Lower transit-km average

Target: average daily transit km drops 15–20% vs v1.

## v3 — Bad Weather Fallback (ALWAYS emitted)

**Always emit.** Even arid / mild destinations need fallbacks — heat-wave indoor refuges, dust-storm shelters, unexpected cold snaps.

Severity of decision-tree triggers scales with `weather_risk`:
- `low` (e.g. Atacama in winter) — still emit, but trigger thresholds are heat / wildfire smoke / cold front
- `medium` (most destinations) — standard rain + wind decision tree
- `high` (monsoon zone Jun–Nov, typhoon-basin season) — full 5-level tree including typhoon protocol

Drives the decision-tree threshold profile chosen — see [`weather_pivot_pattern.md`](weather_pivot_pattern.md).

Transform via [`weather_pivot_pattern.md`](weather_pivot_pattern.md):

### T1. Decision-tree threshold mapping

5 conditions × 5 actions, fixed schema. See pattern doc.

### T2. Per-day swap matrix

For every original day, list:
- Original outdoor item
- Weather threshold that breaks it (light vs heavy vs storm vs typhoon)
- Indoor substitute (drawn from indoor-bank below)
- Cost + booking channel

### T3. Indoor activity bank

Pre-vetted destination-specific options. Categories to populate:
- Museum / cultural (AC, low-traffic)
- Cinema / mall (mainstream English content)
- Indoor waterpark / onsen / spa marathon
- Cooking class / craft workshop
- Specialty café (long-stay friendly)
- Covered rooftop bar (for evening)
- Indoor dining at iconic restaurants

### T4. Booking flexibility tips

- Klook 24hr-cancel filter
- Hotel free-cancel rate
- Airline waiver policy
- Insurance delay clause
- Forecast sources (Windy, local met, PAGASA, Yr.no)
- Local-language phrases for "storm" / "heavy rain"

## Comparison sheet (auto-generated)

The v1-vs-v2 Compare sheet emits a diff table with ~11 rows covering:
- Day-by-day anchor change
- Total spa time
- Avg daily transit km
- Crowd exposure ratings (low/med/high)
- Activity cost per pax
- Nightlife mandatory vs optional
- Active hours per day

## Implementation notes

The v2/v3 transforms are authored by **Claude in-session** (the stage-5 synth
prompt `references/synth_prompts/05_v2_v3_derive.md`) — they require per-destination
judgement and are not a Python module. The deterministic pieces are:

- `scripts/lib/stage_runner.py` — `_stage_5_v2_v3` enforces the v1/v2/v3 day-count parity.
- `scripts/lib/common.py` — `derive_indoor_bank` builds the v3 indoor bank.
- `scripts/build_workbook.py` — emits the v1/v2/v3 sheets.

All output the same trip-data schema (see `templates/trip_data.schema.json`).
