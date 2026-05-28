# Stage 2 — Places

> **Read first:** [`references/learnings.md`](../learnings.md)

## Inputs from prior stages
`metadata{}` and `visa{}` complete.

## What to produce in this stage

Populate the `places[]` array with 15-25 entries covering all required categories for the destination. Each entry represents a discrete visitable location — landmark, restaurant, spa, nightlife venue, or indoor refuge. Entries must contain all mandatory fields plus optional fields where data is available. Use `wiki_title` for any venue with a Wikipedia article; use `alt_search_query` for local venues without Wikipedia coverage so the image fetcher has a usable search string. Mark any venue suitable as a rain or heat refuge with `indoor: true` — this flag feeds the weather contingency plan at stage 6.

## Schema fields to fill

- `places[].key` (snake_case slug, unique within the array)
- `places[].name` (display name, native script acceptable with romanisation)
- `places[].category` (enum: `iconic`, `hidden_gem`, `food`, `spa`, `nightlife`, `hotel`, `indoor_backup`)
- `places[].area` (neighbourhood or district name)
- `places[].wiki_title` (underscored Wikipedia article title, e.g. `Dragon_Bridge_(Da_Nang)`)
- `places[].alt_search_query` (free-form search string for venues without a Wikipedia article)
- `places[].description` (1-3 sentences; concrete details, no ad-copy)
- `places[].lat` / `places[].lon` — leave blank; stage runner fills via Nominatim
- `places[].distance_km_from_base` / `places[].travel_min_from_base`
- `places[].price_local` (integer in local currency, or null) / `places[].price_label` (human-friendly tag)
- `places[].when` (suggested itinerary slot, e.g. `Day 2 evening`)
- `places[].indoor` (bool — flag rain/heat refuges)
- `places[].duration` (expected visit length, e.g. `30min`)
- `places[].opening_hours` (string or null)
- `places[].links[]` (array of `{"label": "...", "url": "..."}` pairs)

## Quality bar

- 15-25 entries total for a 5-day trip; scale proportionally for shorter/longer trips.
- Each category appears at least twice, EXCEPT `hotel` (covered by stage 3) and `indoor_backup` (minimum 3 entries for tropical or monsoon destinations).
- `description` is 1-3 sentences. Use concrete, specific details — opening times, signature dishes, architectural features. No phrases like "amazing experience", "must-visit", or "hidden treasure".
- `wiki_title` uses underscores, no URL-encoding, no `https://` prefix. The stage 2 runner probes Wikipedia for each title and flags misses in run notes.
- For every Wikipedia miss, set `alt_search_query` to a free-form Google search string the image fetcher can use (venue name + city + type).
- `links[]` includes at minimum a Google Maps entry plus one review or official site where available.
- `indoor: true` is required on any venue that functions as a shelter from rain or extreme heat. This auto-derives into `weather_plan_b.indoor_bank` at stage 6.

## Reference snippets

```json
{
  "places": [
    {
      "key": "dragon_bridge",
      "name": "Dragon Bridge",
      "category": "iconic",
      "area": "Han River",
      "wiki_title": "Dragon_Bridge_(Da_Nang)",
      "description": "Six-lane road bridge with dragon sculpture. Fire-and-water show Fri/Sat/Sun 21:00.",
      "distance_km_from_base": 4.2,
      "travel_min_from_base": 12,
      "price_local": 0,
      "price_label": "Free",
      "when": "Day 2 evening",
      "indoor": false,
      "duration": "30min",
      "opening_hours": "24h (show Fri/Sat/Sun 21:00)",
      "links": [
        {"label": "Google Maps", "url": "https://maps.app.goo.gl/example"},
        {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Dragon_Bridge_(Da_Nang)"}
      ]
    },
    {
      "key": "bun_cha_ca",
      "name": "Bún Chả Cá Bà Phiến",
      "category": "food",
      "area": "Hai Chau",
      "alt_search_query": "Bun Cha Ca Da Nang local restaurant",
      "description": "Locals' fish-cake noodle soup. Counter-service, lunch only.",
      "distance_km_from_base": 3.1,
      "travel_min_from_base": 9,
      "price_local": 35000,
      "price_label": "₫35-50k",
      "indoor": true,
      "duration": "30min",
      "opening_hours": "07:00-13:00",
      "links": []
    }
  ]
}
```

## When done, run

```
python .claude/skills/itinerary-builder/scripts/synthesize.py --slug <slug> --stage 2
```

If errors: patch, re-run. Stage 2 also auto-geocodes + probes Wikipedia. Notes flag misses — add `alt_search_query` where Wikipedia 404s.
