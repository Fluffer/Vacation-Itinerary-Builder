# Pick-ONE-Bundle Pricing Pattern

## The mistake to avoid

When a destination has flagship activities bundleable via Klook / Pelago / Viator / Get Your Guide, naïvely listing every line item in the itinerary leads to **double-counting**:

```
07:30  Drive to Ba Na          | 850,000 VND  (private Grab one-way)
09:00  Cable car combo ticket  | 1,050,000 VND  (gate price)
12:30  Lunch at French Village | 350,000 VND  (per pax)
15:30  Drive back              | 850,000 VND  (private Grab return)
                          TOTAL  3,100,000 VND
```

But the same trip booked via Klook GROUP DAY TOUR is one ticket: **1,200,000 VND all-in** (transport + cable car + lunch + guide bundled).

## The rule

For any flagship activity where bundling exists, present **PATHS** as mutually-exclusive booking strategies. Sum within a path. NEVER sum across paths.

## Sheet 13 layout

```
🎡 BA NA HILLS — PICK ONE BUNDLE (do NOT add rows together)

PATH 1 — Klook GROUP DAY TOUR     | Klook shared bus pkg    | 1,200,000 | ALL-IN: shuttle+ticket+lunch+guide
PATH 2 — Klook VIP private car    | Klook private bundle    | 1,800,000 | car+driver+ticket; lunch extra
PATH 3 — Concierge Grab + ticket  | self-assembled          | 1,750,000 | Grab 1.6M/2 + Klook ticket 950k
PATH 4 — Cable car ticket only    | Sun World gate          | 1,050,000 | TICKET only; transport extra

Optional: Alpine Coaster (extra)  | on-site                 |   200,000 |
Optional: Fantasy Park            | on-site                 |   350,000 |
Optional: Debay Wine tasting      | on-site                 |    50,000 |
```

Top of sheet must have a **YELLOW BANNER** warning:
> ⚠️ READ FIRST: For bundled activities PICK ONE PATH only — do NOT add rows. Klook GROUP DAY TOURS bundle transport + ticket + lunch in ONE price.

## Itinerary sheet rows

In the day-by-day grid, the bundled activity gets **one ALL-IN row** referencing Sheet 13:

```
07:30  Ba Na ALL-IN — pick ONE path (see Sheet 13)  |  72 km  | 110 min | 1,300,000 | mid-path estimate; alt paths Sheet 13
08:30  Arrive Ba Na cable car                       |          |         |          |
09:00  Cable car + Golden Bridge                    |  5.8 km  |  18 min |        0 | included in 07:30
10:30  French Village + pagoda                      |  1.5 km  |  45 min |        0 | included
...
```

The 07:30 row absorbs the bundle cost. Subsequent rows show `0` for VND but still log distance/time. The day-total SUM formula still works correctly.

## Where bundles typically exist

- **Mountain/cable-car resorts** (Ba Na Hills, Cable Car Langkawi, Genting): group day tour incl transport + ticket + lunch
- **Scenic mountain passes** (Hai Van, Cameron Highlands): group van + English guide + multiple stops
- **Heritage sites at distance** (Mỹ Sơn, Bagan ruins): half-day or full-day shared/private options
- **Island day trips** (Cù Lao Chàm, Phi Phi): boat + lunch + park fee + snorkel gear all bundled
- **Hot springs / onsen complexes**: day pass usually all-in

## Where bundles do NOT exist

- Walking/wandering districts (Hoi An Old Town) — just pay the entry pass
- Free attractions (Lady Buddha, beaches) — only transport cost
- Restaurants — never bundle prices
- Cafes — never bundle

## Channels to compare

For each bundleable activity, list at minimum:
1. **Klook GROUP DAY TOUR** (cheapest, shared van)
2. **Klook PRIVATE** (per car, 2–4 pax split)
3. **Pelago / Viator** alternative if pricing differs
4. **Gate / walk-up** (ticket only baseline)
5. **Self-assembled** (Grab + ticket separately) — show math

## Verification

Re-check pricing 2 weeks pre-travel via:
- Klook listings page for the activity (region-locked, use SG/HK/PH version)
- Pelago equivalent
- Official operator site (Sun World, Vietravel, etc.)

Prices drift seasonally — annotate "as of YYYY-MM-DD" if pulled at build time.
