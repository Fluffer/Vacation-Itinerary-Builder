# Sheet Schemas

All sheets use Arial font, professional formatting. Conditionally emitted — only build sheets whose data exists.

## Universal styling

```python
ARIAL = 'Arial'
HEADER_FILL = PatternFill('solid', start_color='1F4E78')
HEADER_FONT = Font(name=ARIAL, bold=True, color='FFFFFF', size=11)
TITLE_FILL = PatternFill('solid', start_color='2E75B6')
ALT_FILL = PatternFill('solid', start_color='F2F2F2')   # alternating rows
WARN_FILL = PatternFill('solid', start_color='FFF2CC')   # warning
GOOD_FILL = PatternFill('solid', start_color='E2EFDA')   # totals
V2_FILL = PatternFill('solid', start_color='7030A0')     # relaxed variant header
V3_FILL = PatternFill('solid', start_color='595959')     # bad-weather variant header
GEM_FILL = PatternFill('solid', start_color='FCE4D6')    # hidden-gem tag
```

## Sheet list (conditional)

Sheets are addressed **by name** everywhere (the leading numbers in the workbook
are display-only). Emitted order follows `build_workbook.py`'s `desired_order`.

| Sheet | Always emit? | Source data |
|---|---|---|
| Overview | yes | trip metadata + risk flags |
| Booking Timeline | yes | activity list w/ lead times |
| v1 Daily Itinerary | yes | parsed source doc enhanced |
| v2 Relaxed Pace | **yes (always)** | substitution table |
| v3 Weather Itinerary | **yes (always)** | `itinerary.v3_weather` |
| v3 Bad Weather Plan B | **yes (always)**; threshold profile varies by weather_risk | weather decision tree + indoor swaps |
| v1 vs v2 Compare | yes (since v2 always emits) | diff table |
| Accommodation | yes | hotel options |
| Food, Spas, Nightlife | yes | POI list |
| Hidden Gems & Swaps | if alternatives ≥ 5 (auto-generated if missing) | POI database |
| Activity Pricing | if bundleable activities exist | pick-one-path matrix |
| Distance Matrix | yes | base hotel → every POI |
| Budget | yes | per-pax costs |
| Practical Info | yes | visa, currency, plug, emergency |
| Pre-Departure Checklist | yes | rolled up from validation flags |

## Sheet 1 — Overview

Key-value layout, merged columns 2–4. Sections:
1. Trip metadata block (dates, origin, destination, passport, visa, base hotel, currency, climate, power, emergency)
2. Risk Flags & Mitigations (10 items, yellow-fill labels)
3. Variant pointer note (purple band — directs to the v1 / v2 / v3 sheets)

## Sheet 2 — Booking Timeline

4 columns: Window | Lead time | Action | Why. ~10 rows.

## v1 / v2 / v3 Daily Itinerary sheets

9 columns: Time | Activity | From→To | Dist (km) | Travel (min) | Cost (VND) | Cost (SGD) | Notes | ✓

Per day:
- Day-title row (full-width, blue/purple band)
- Header row
- Activity rows
- Day-total row with `=SUM()` formulas for Dist, Travel, VND, SGD

Distance/time are **per-segment travel from previous point**, not cumulative.

## Sheet 4 — Accommodation

6 columns: Hotel | Tier | Rating | SGD/night (low) | SGD/night (high) | Notes
Recommendation banner below table.

## Sheet 5 — Food, Spas, Nightlife

3 sub-tables, each 5 columns: Place | Area | Price (VND) | Notes | When in itinerary

## Sheet 6 — Practical Info

Key-value layout. ~22 rows covering: visa, passport validity, currency, ATM, cards, cash, tipping, SIM, power, water, weather, dress code, apps, language, emergency, embassies, insurance.

## Sheet 7 — Pre-Departure Checklist

3 columns: Category | Item | Done? (☐). Groups: Documents, Money, Tech, Bookings, Pack, Pre-flight.

## Sheet 8 — Budget

5 columns: Category | VND (low) | VND (high) | SGD (low) | SGD (high)

- Exchange-rate cell at top (B3, blue text, warn fill) — drives all SGD formulas
- Ground costs subtotal at end
- Flight & hotel section below (direct SGD)
- GRAND TOTAL at bottom (blue band)

Pattern: `=B6/$B$3` for VND→SGD conversion.

## Sheet 10 — Hidden Gems & Swaps

Categorised: NATURE/SCENIC, BEACHES, FOOD, COFFEE, CULTURE, WELLNESS. Each category gets header band + 5-col table: Place | Distance from base | Travel time | Why it stays quiet | Notes/When | Tried?

## Sheet 11 — Distance Matrix

5 columns: From | To | Distance (km) | Travel time (min) | Typical fare (VND).
~25 rows covering: airport, base, all major POIs, day-trip targets. Most rows have base hotel as the "From".
Append a Grab/transport tips block below (6 bullet rows).

## Sheet 12 — v1 vs v2 Compare

4 columns: Item | v1 — Standard | v2 — Relaxed Less-Touristy | Why change. ~11 rows.

## Sheet 13 — Activity Pricing

**Critical pattern:**
- Top banner: warning "PICK ONE PATH — do NOT add rows" w/ yellow fill
- Organised by activity category, each category as a header band
- Path rows: `PATH 1 — Klook GROUP DAY TOUR` | channel | per-pax VND | what's bundled
- After path rows, OPTIONAL extras as separate rows
- Auto-calc SGD via `=C{r}/<rate-ref>` where `<rate-ref>` is the currency cell on the Budget sheet (e.g. `'Budget'!$B$3`) — never a hardcoded rate

Categories: BA NA HILLS (or equivalent flagship), HAI VAN PASS (or scenic drive), HOI AN (or culture core), MARBLE MOUNTAINS (or hike), main pagoda, day-trip alts, spas, transport, nightlife, food markers.

## v3 Bad Weather Plan B sheet

Sections:
1. **Decision tree** — 5 conditions × Trigger × Action. Conditions: Clear / PM showers / All-day rain / Tropical storm / Typhoon warning
2. **Per-day swap matrix** — 6 cols: Original item | Why at risk | Trigger | Plan-B action | Alt VND | Channel
3. **Indoor activity bank** — 19+ vetted options: 5 cols Activity | Area | VND | Duration | Notes
4. **Booking flexibility tips** — Klook 24hr cancel, Agoda free-cancel, airline waivers, insurance, forecast sources, local cues

See [`weather_pivot_pattern.md`](weather_pivot_pattern.md) for the decision-tree thresholds.
