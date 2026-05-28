# Enhancement Rules — Auto-Apply to v1

Rules applied to the parsed source doc before emitting v1. Each rule has a trigger + transform.

## R1. Single hotel base (trips ≤ 7 days)

**Trigger:** Trip duration ≤ 7 days AND destination has good intra-city transport.

**Transform:** Recommend one anchor hotel area; flag in Overview sheet. Avoid 1-night Hoi An / Phuket-island / inner-city splits which eat half a day to luggage-shuffle.

Exceptions: trips ≥ 7 days, multi-island, multi-city itineraries explicit in source.

## R2. Distance + travel-time columns

**Trigger:** Always.

**Transform:** For every itinerary row with a movement (Grab / walk / drive), add:
- `Dist (km)` — segment km from previous point
- `Travel (min)` — typical-traffic time

Use Google Maps Distance Matrix knowledge OR a per-trip `distances.json`. Add buffer 30–50% for rush hour (16:30–18:30).

## R3. Airport buffer ≥ vendor recommendation

**Trigger:** Always.

**Transform:** Check the carrier's published international-departure check-in window. If source has tighter buffer, push hotel-departure earlier:
- Scoot: 3 hours int'l
- AirAsia / JetStar: 3 hours int'l
- Full-service (SQ, EVA, JAL): 2.5–3 hours int'l
- Domestic VN: 2 hours

Add a risk flag on Overview if source-stated buffer was tight.

## R4. Visa accuracy

**Trigger:** Always — high error rate.

**Transform:** Validate via Ollama:
- Traveler nationality + destination pairing
- Days visa-free OR e-visa required
- Passport validity ≥ 6 months beyond return
- Onward-ticket evidence requirement

Known correct rules (manual fallback):
- Singapore passport → Vietnam: 30 days visa-free
- Philippines passport → Vietnam: 21 days visa-free (NOT 30)
- USA passport → Vietnam: e-visa required
- EU passport → Vietnam: 45 days visa-free (Schengen 12 nationalities)

Verify rules at time of build — they change.

## R5. Currency rate accuracy

**Trigger:** Always.

**Transform:** Use a defensible mid-rate (XE / OANDA) at build time. Default Excel rate cell to that value. Annotate "as of YYYY-MM-DD" in Overview.

Common mistake: stale rate from internet 6 months back can be off 5–10%.

## R6. Power plug accuracy

**Trigger:** Always — frequent source mistake.

**Transform:** Lookup destination plug standard. Singapore (Type G) does NOT fit:
- Vietnam (A/C/F)
- Thailand (A/B/C/O)
- Indonesia (C/F/G — G works in some hotels)
- Japan (A/B, 100V — voltage difference)

Flag in Practical Info sheet with "SG/UK plugs DO NOT FIT" warning where true.

## R7. Bundle pricing consolidation

**Trigger:** Source itinerary lists separate transport + ticket + lunch for an activity that vendors offer as a bundle.

**Transform:** Replace with ALL-IN row referencing Sheet 13. See [`pricing_pattern.md`](pricing_pattern.md).

## R8. Risk-fatigue detection

**Trigger:** Day has ≥ 1 full-day outdoor activity AND a late-night anchor (≥ 21:30).

**Transform:** Append risk flag: "Day X: full outdoor + late nightlife = high fatigue; consider half-day OR skip nightlife".

Common patterns to catch:
- Mountain resort + pub crawl same day
- Sunrise temple + dinner cruise
- Two long-distance day-trips back-to-back

## R9. Same-day combo split (for v2)

**Trigger:** Day combines 2+ outdoor anchors >2 km apart.

**Transform:** Only applies to v2 generation. Move one anchor to a free slot on another day. Add to comparison sheet diff.

## R10. Hidden gem augmentation

**Trigger:** Source itinerary lacks ≥ 1 alternative POI per category (food, beach, café, culture, scenic).

**Transform:** Pull 20+ vetted alternatives from local-knowledge sources. Populate Sheet 10.

## R11. Weather plan B — always emit

**Trigger:** Always (skill's core promise — every itinerary has all 3 variants).

**Transform:** Emit Sheet 14 with destination-specific indoor bank + decision tree. Threshold profile chosen by `weather_risk` (low / medium / high) — see [`weather_pivot_pattern.md`](weather_pivot_pattern.md).

## R12. Booking-flex defaults

**Trigger:** Always.

**Transform:** Add to Booking Timeline:
- T-3 mo: hotel Free Cancellation
- T-2 mo: pre-book bundleable activities (Klook 24hr cancel filter)
- T-1 wk: WhatsApp spas / operators to confirm
- T-72hr: airline web check-in opens

## R13. Sunrise-shift opportunity

**Trigger:** v2 generation, popular headline attraction.

**Transform:** Move to 05:30–06:30 start where:
- Site opens (or is accessible) at dawn
- Empty vs midday crowds
- Photos better (golden hour)

Examples: Lady Buddha (Son Tra), Mỹ Sơn ruins, Angkor Wat, Borobudur, fishing wharves, beach sunrises.

## Implementation

Each rule in `scripts/lib/rules.py` as a pure function:

```python
def rule_r1_single_hotel(trip: dict) -> dict: ...
def rule_r3_airport_buffer(trip: dict) -> dict: ...
```

Apply in order:

```python
RULES = [rule_r1_single_hotel, rule_r2_distance, rule_r3_airport_buffer, ...]
for rule in RULES:
    trip = rule(trip)
```

Each rule appends to `trip['changes_applied']` for audit / changelog in the Word doc.
