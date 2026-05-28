# itinerary-builder (project)

Project root for the **itinerary-builder** Claude Code skill.

The skill itself lives at [`.claude/skills/itinerary-builder/`](.claude/skills/itinerary-builder/) and is auto-discovered by Claude Code whenever this folder is the working directory.

```
itinerary-builder/                        ← project root (this folder)
├── .claude/
│   └── skills/
│       └── itinerary-builder/            ← the skill (auto-discovered)
│           ├── SKILL.md
│           ├── references/               (design docs)
│           ├── scripts/                  (Python pipeline)
│           └── templates/                (data contract)
├── trips/                                ← workspace (per-trip outputs)
│   ├── da-nang/                          (reference example)
│   └── manila/                           (built 28 May 2026)
├── Da_Nang_Booking_Strategy_v4.xlsx      ← golden reference output
└── README.md
```

## How Claude finds the skill

Open this folder as the project in Claude Code. Skills under `.claude/skills/` are auto-discovered. Ask:

> "Plan a trip to Tokyo, Aug 14-18 2026, PH passport."

Claude invokes `itinerary-builder` automatically.

## How to install the skill in another project

Copy `.claude/skills/itinerary-builder/` into the target project's `.claude/skills/` dir. Or install user-globally at `~/.claude/skills/itinerary-builder/` for any-project discovery.

## Quick manual run (no Claude)

```powershell
$SKILL = ".claude/skills/itinerary-builder"

# Hand-build trips/<slug>/data.json from templates/trip_data.schema.json
# Then:
pip install python-docx openpyxl Pillow staticmap
python "$SKILL/scripts/run_all.py" --slug my-trip --downloads-copy
```

Python 3.10+ (tested 3.14 on Windows 11).

## Output guarantee

Every run produces a 14-sheet Excel workbook + illustrated Word doc:

| # | Sheet |
|---|---|
| 1 | Overview + Risk Flags |
| 2 | Booking Timeline |
| 3 | Daily Itinerary v1 (packed) |
| 4 | Accommodation |
| 5 | Food / Spas / Nightlife |
| 6 | Practical Info |
| 7 | Pre-Departure Checklist |
| 8 | Budget (w/ FX formula) |
| 9 | Relaxed Pace v2 |
| 10 | Hidden Gems & Swaps |
| 11 | Distance Matrix |
| 12 | v1 vs v2 Compare |
| 13 | Activity Pricing (pick-ONE bundles) |
| 14 | Bad Weather Plan B (decision tree + per-day swaps + indoor bank) |

Sheets emit conditionally on data presence. v1/v2/v3 always emitted (skill's core promise).

Reference output: [`Da_Nang_Booking_Strategy_v4.xlsx`](Da_Nang_Booking_Strategy_v4.xlsx).
