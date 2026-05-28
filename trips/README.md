# trips/

Per-trip working directories. One subfolder per trip, named by slug.

## Structure

```
trips/
├── README.md           (this file)
└── <slug>/
    ├── data.json       (structured trip data — schema: templates/trip_data.schema.json)
    ├── source.docx     (optional copy of source draft)
    ├── images/         (downloaded photos + rendered maps)
    │   ├── *.jpg       (POI photos)
    │   ├── map_regional.jpg
    │   └── map_city.jpg
    ├── unvalidated.md  (facts pipeline couldn't verify — manual review needed)
    ├── validate_prompts.md  (validation checklist)
    ├── <slug>_Booking_Strategy.xlsx  (final workbook)
    └── <slug>_Trip_Guide.docx        (final illustrated guide)
```

## Workflow

1. Create `trips/<slug>/` directory
2. Copy source draft to `trips/<slug>/source.docx`
3. Build `trips/<slug>/data.json` by parsing the source + applying enhancement rules
   (see `references/enhancement_rules.md`). Use `templates/trip_data.schema.json`.
4. Optionally validate facts via Claude (using Ollama MCP tools) — write
   verified values back into data.json
5. Run orchestrator: `python ../scripts/run_all.py --slug <slug>`
6. Outputs land in this directory + optionally copied to `~/Downloads/`

## Reference implementation

`trips/da-nang/` is a complete real example built for Aug 14–18 2026
Singapore → Da Nang. Use it as a template when starting a new trip.
