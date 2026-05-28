# Weather Pivot Pattern — Bad Weather Plan B Template

Generic decision-tree template. Plug in destination-specific thresholds + indoor swaps.

## Decision tree — 5 conditions

| Condition | Trigger (forecast) | Action |
|---|---|---|
| ☀️ Clear / scattered cloud | Rain <30%, wind <20 km/h | Run v1 or v2 unchanged |
| ⛅ Afternoon showers expected | Rain 30–60% PM only | Front-load outdoor AM; indoor PM (spa, café, museum); rain shell on hand |
| 🌧️ All-day rain | Rain 60–90%, wind 20–40 km/h | Pivot to FULL INDOOR. Cable car may close. Avoid motorbike tours |
| ⛈️ Tropical storm / heavy depression | Rain >90%, wind 40–80 km/h | Stay in city. No mountain pass, no remote pagoda, no cave hikes |
| 🌀 Typhoon warning issued | Named cyclone within 200 km | Stay hotel. Stock water + snacks. Charge devices. Monitor official met hourly. Insurance ready |

## When to emit

**ALWAYS emit Sheet 14.** Skill's core promise — every itinerary has all 3 variants.

Threshold profile chosen by `weather_risk`:

| Risk | Examples | Trigger profile |
|---|---|---|
| `low` | Atacama, Death Valley, Egypt winter | Heat-wave (>40°C), dust storm, wildfire smoke AQI |
| `medium` | Most temperate destinations | Rain probability + wind speed standard tree |
| `high` | Monsoon zone Jun–Nov, typhoon basins | Full 5-level: clear / PM showers / all-day rain / tropical storm / typhoon |

Examples of `high`:
- Vietnam Central/South: Jun–Nov (rain ramps Sep)
- Philippines Aug–Oct (peak typhoon)
- Thailand Andaman: May–Oct
- Japan Sep typhoon edge
- Bangladesh / India SW monsoon Jun–Sep

Examples of `low`:
- Saudi Arabia / UAE outside Aug
- Greek islands Jun–Aug (heat-wave swap dominates)
- Iceland Jul (different threshold profile — wind + ash)

## Per-day swap matrix structure

6 columns:
1. **Original item** — exactly as in v1/v2
2. **Why at risk** — concrete failure mode (e.g. "cable car closes in lightning", "limestone slippery")
3. **Trigger** — which decision-tree row activates the swap
4. **Plan-B action** — concrete swap with location
5. **Alt VND** — cost
6. **Channel** — where to book

For each variant day, audit every outdoor item and write a swap row.

## Indoor activity bank — categories to populate

Destination-specific list (15–20 items) covering:

| Category | Example (Da Nang) |
|---|---|
| Museum/cultural (AC) | Cham Museum, Da Nang Museum, Fine Arts Museum |
| Indoor waterpark/onsen | Mikazuki Japanese Resort 365 |
| Cinema/mall | Lotte Cinema Vincom Plaza |
| Cooking class | Red Bridge Cooking School, Tra Que Herb Village |
| Craft workshop | Hoi An Lantern-Making, Silk Village, Cao Lầu noodle |
| Photo museum / silent space | Réhahn Photo Museum, Reaching Out Tea House |
| Specialty café | 43 Factory, Mê Cà Phê |
| Iconic indoor restaurant | Pizza 4P's, Madam Lân (colonial villa) |
| Covered rooftop bar | Sky36 |
| Spa marathon | Babylon Royal 150-min + Queen 90-min different sessions |
| Heritage site indoor | Mỹ Sơn Sanctuary (partly covered ruins) |
| Han River dinner cruise | (covered lower deck) |

Maintain per-destination bank in `trips/<slug>/indoor_bank.json`.

## Booking flexibility tips — 9 standard items

1. **Klook bookings** — filter "Free cancellation up to 24hr". Decide outdoor 2 days ahead via Windy.
2. **Hotel rate** — Agoda/Booking Free Cancellation 5–10% more, lets you extend a day if flights delayed.
3. **Airline flight** — most majors waive change fees during published typhoon warnings on their advisories page.
4. **Travel insurance** — pays >6hr delay (meals, hotel). Keep receipts; file within 30 days.
5. **Private driver** — books via hotel concierge or Klook private; they refund/reschedule for impassable roads.
6. **Spas** — WhatsApp booking, usually flexible same-week, no deposit.
7. **Pub crawl / nightlife** — DM the operator on FB/Instagram morning-of for run status.
8. **Forecast sources** — Windy.com (radar + multi-model), local met (e.g. nchmf.gov.vn), PAGASA, Yr.no.
9. **Local cues** — hotel staff vernacular for "typhoon" / "heavy rain" — believe them over apps.

## Localised phrases (always include)

For the destination language:
- "Typhoon" / "cyclone"
- "Heavy rain"
- "Safety first"
- "Cancel" / "reschedule"

E.g. Vietnamese: `bão` (typhoon), `mưa lớn` (heavy rain), `an toàn` (safety).
