# Itinerary Synthesizer — Learnings

> Curated, append-only. Loaded by every stage of the staged synthesizer.
> Each entry should be one-line actionable. Tag with run_id when adding via `--stage learn`.

## Tropical SE-Asia
- (none yet — populated as runs complete)

## Non-tropical EU
- Lisbon mid-Aug: heat-wave (35-40C) is the real risk, not rain. Use 14:00-16:00 indoor refuge slot. Source: run 2026-05-29T_synthetic_lisbon.
- Schengen visa for PH passport: physical Schengen visa required (`e_visa_required: false`), 90-day max. Distinguish from "visa-exempt N days" bilateral rules common in SE-Asia.
- FX rate to SGD as decimal (EUR ≈ 0.68 SGD) works fine; budget `*_local` fields in EUR are small integers.
- 5-level weather decision_tree labels are free strings — repurpose `typhoon warning` slot as `extreme heat event` for EU summer destinations.

## Cold / Northern
- (none yet)

## Pricing
- (none yet)

## Place categories
- (none yet)

## Visa / passport gotchas
- PH passport: bilateral visa-exempt only for ASEAN + select bilaterals (VN, MY, TH, SG, ID, etc). Outside ASEAN, default is visa-required.
