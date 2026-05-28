# Itinerary Synthesizer — Design Spec

**Date:** 2026-05-29
**Status:** Approved (pending user spec review)
**Scope:** Add a staged in-session LLM-driven synthesizer to the `itinerary-builder` skill that produces a fully-populated `trips/<slug>/data.json` from `destination + dates + passport`, with logging + feedback-driven self-improvement.

---

## 1. Background

The existing `itinerary-builder` skill renders a 14-sheet Excel workbook + illustrated Word doc from a hand-authored `trips/<slug>/data.json` (800–1500 lines for a 5-day trip). Current Phase 1 Path B requires Claude to compose this file by hand against the schema — "no automated synthesizer exists." This spec defines that synthesizer.

Pipeline renderers (`build_workbook.py`, `build_docx.py`, `build_map.py`, etc.) are out of scope and remain untouched.

## 2. Goals + non-goals

### Goals (v1 ship)
- Given `destination + dates_start + dates_end + passport`, produce a schema-valid `data.json` that renders 14 sheets + Word doc cleanly.
- Content density approximating hand-authored Manila/Da Nang fixtures: 15–25 places, 4–7 hotels, 4–6 activity bundles, three full itinerary variants.
- Production-grade: integrated Ollama fact-validation on visa/weather/pricing (non-blocking, existing pattern).
- Resumable mid-flight: any stage re-runnable idempotently.
- Self-improving: every run logged; user feedback captured; consolidated learnings re-injected into future synth runs.

### Non-goals (v1)
- Free-form natural-language intake ("plan me something fun in Asia").
- Multi-pax mixed-passport visa handling.
- Save-as-template / derive-Tokyo-from-Bali.
- Auto-rebuild on schema migration.
- Modifying renderers or workbook layout.

## 3. Decisions (already locked)

| Decision | Choice | Notes |
|---|---|---|
| LLM engine at skill runtime | **In-session Claude** | No SDK plumbing. Skill provides scaffold; Claude in chat composes. |
| LLM use during build/test | **Ollama (deepseek-pro, glm, minimax) fair game** | For prompt review, code review, fact-validation prompt tuning. Not used at runtime. |
| Staging strategy | **Linear staged (Approach A)** | Six stages: metadata → places → hotels/pricing/budget → v1 → v2/v3 derive → ancillary. Validator + auto-deriver between stages. |
| Pipeline integration | **Separate synthesize step, then run_all.py** | Synthesis failures cannot poison renderer. Clean handoff via committed `data.json`. |
| Success bar v1 | **Production-grade with fact validation** | Schema-valid + renders clean + Ollama fact-validate pass + feedback loop wired. |
| Subagent strategy | **Parallel where independent** | Waves 1, 3, 5 dispatch parallel; waves 0, 2, 4 serial. |

## 4. Architecture

```
.claude/skills/itinerary-builder/
├── SKILL.md                            (update Phase 1 Path B → staged synth)
├── references/
│   ├── workflow.md                     (update Phase 1 + add Phase 10.5)
│   ├── learnings.md                    ← NEW append-only curated lessons
│   └── synth_prompts/                  ← NEW staged templates
│       ├── 01_metadata_visa.md
│       ├── 02_places.md
│       ├── 03_hotels_pricing_budget.md
│       ├── 04_v1_itinerary.md
│       ├── 05_v2_v3_derive.md
│       └── 06_ancillary.md
├── scripts/
│   ├── synthesize.py                   ← NEW thin CLI orchestrator
│   ├── lib/
│   │   ├── common.py                   (existing)
│   │   ├── schema_check.py             ← NEW jsonschema wrapper
│   │   ├── geocode.py                  ← NEW Nominatim + disk cache
│   │   ├── wiki_precheck.py            ← NEW Wikipedia REST probe + cache
│   │   ├── stage_runner.py             ← NEW per-stage harness
│   │   └── run_logger.py               ← NEW manifest + jsonl event writer
│   └── (renderers untouched)
├── templates/
│   └── trip_data.schema.json           (existing, unchanged)
└── runs/                               ← NEW per-run append-only log
    └── <ISO_timestamp>_<slug>/
        ├── manifest.json
        ├── stages.jsonl
        ├── data.snapshot.json
        └── feedback.md
```

**Execution surfaces:**
- **In-session skill flow (runtime):** Claude reads `synth_prompts/0N_*.md` sequentially. After each stage, writes `data.json` and runs `python synthesize.py --slug <slug> --stage <N>` to validate.
- **CLI (`synthesize.py`):** Thin Python entry. Never calls an LLM. Validates current data.json, runs geocode batch, runs wiki precheck, runs Ollama fact-validate, writes run log.

**Hard rule:** `synthesize.py` invokes no LLM. All composition is Claude in-session.

## 5. Components

### `lib/schema_check.py`
- `validate(data: dict, partial: bool = False) -> list[str]` — wraps `jsonschema.Draft7Validator`.
- `partial=True` skips top-level `required` enforcement (mid-stage use).
- Returns list of `f"{path}: {message}"` strings. Empty = pass.
- CLI: `python -m lib.schema_check <path-to-data.json>`.

### `lib/geocode.py`
- `geocode(name, area, country) -> (lat, lon) | None` — Nominatim, `User-Agent: itinerary-builder/1.0`, 1.1s inter-call sleep, 5s timeout.
- Cache: `trips/<slug>/.cache/geocode.json`, key `f"{name}|{area}|{country}"`.
- `geocode_batch(places, country)` — fills lat/lon in-place where missing; returns miss count.
- Rate-limit handling: on HTTP 429, sleep 30s + 1 retry. Then mark miss, continue.

### `lib/wiki_precheck.py`
- `precheck(wiki_title) -> bool` — HEAD/GET `https://en.wikipedia.org/api/rest_v1/page/summary/<title>`. 200 = hit, 404/missing = miss.
- `precheck_places(places) -> list[dict]` — returns `[{key, wiki_title, hit}]`.
- Cache: `trips/<slug>/.cache/wiki.json`.

### `lib/stage_runner.py`
- `run_stage(slug, stage_num) -> StageResult` — load `data.json`, dispatch stage-specific validators + derivers, write back.
- Per-stage hooks:
  - **Stage 1 (metadata + visa):** partial schema on `metadata` + `visa` blocks.
  - **Stage 2 (places):** geocode_batch → wiki_precheck → partial schema on `places[]`.
  - **Stage 3 (hotels/pricing/budget):** partial schema on those three blocks.
  - **Stage 4 (v1):** row-invariants (time format, km/min not null for transit rows, every place-key reference resolves to `places[]`).
  - **Stage 5 (v2/v3):** day-count matches v1; basic schema on both variant arrays.
  - **Stage 6 (ancillary):** auto-derive `distance_matrix` + `weather_plan_b.indoor_bank`; **full strict schema check**.
- `final_validate(slug)` — full strict schema + call `validate_facts.py` (Ollama, non-blocking, → `unvalidated.md`).
- `StageResult` dataclass: `passed: bool, errors: list[str], notes: list[str], duration_s: float`.

### `lib/run_logger.py`
- `RunLogger(slug)` — context manager. On `__enter__` creates `runs/<ISO>_<slug>/`, writes initial `manifest.json`. On stage events, appends to `stages.jsonl`. On `__exit__` finalises manifest with end-time + outcome.
- `snapshot_data(slug)` — copies `trips/<slug>/data.json` → `runs/<run_id>/data.snapshot.json`.
- `capture_feedback(slug, text)` — writes `feedback.md`, sets `manifest.feedback_captured=true`.
- `consolidate(days=30)` — for `--learn` subcommand: scan recent `feedback.md` files, surface candidate `learnings.md` entries for human review.

### `scripts/synthesize.py`
- CLI: `python synthesize.py --slug <slug> --stage <1-6|final|learn>`.
- Dispatches to `stage_runner.run_stage` / `final_validate` / `run_logger.consolidate`.
- Prints pass/fail per stage + next-step hint.
- Exit code 0 pass, 1 fail.
- Auto-creates `runs/<ISO>_<slug>/` on first stage call; reuses for subsequent stages of same synthesis session via `runs/.current_run` pointer file.

### `references/synth_prompts/0N_*.md`
Each template structured:
```
## Stage N — <name>
## Inputs (from prior stages)
## What to produce
## Schema fields to fill
## Quality bar (from learnings.md + reference snippets)
## Validation command
```
Stages read `references/learnings.md` at the top of every prompt — that's how user feedback influences future runs.

## 6. Data flow

```
INTAKE GATE (existing intake.md)
  ↓
STAGE 1: metadata + visa  →  validate partial  →  log event
  ↓
STAGE 2: places  →  geocode_batch  →  wiki_precheck  →  validate partial
  ↓
STAGE 3: hotels + activity_pricing + budget  →  validate partial
  ↓
STAGE 4: v1_standard itinerary  →  row-invariants  →  validate partial
  ↓
STAGE 5: v2_relaxed + v3_weather (derived from v1)  →  day-count match  →  validate partial
  ↓
STAGE 6: ancillary blocks  →  auto-derive distance_matrix + indoor_bank  →  STRICT schema
  ↓
FINAL: validate_facts.py (Ollama, non-blocking)  →  unvalidated.md
  ↓
SNAPSHOT: copy data.json → runs/<id>/data.snapshot.json
  ↓
HANDOFF: invoke run_all.py
  ↓
DELIVERY: workbook + docx → manifest.delivered_files populated
  ↓
FEEDBACK CAPTURE: prompt user → runs/<id>/feedback.md (skippable)
  ↓
RunLogger finalises manifest.json (ended_at, feedback_captured)
```

Each stage event appended to `runs/<id>/stages.jsonl` as one line.

## 7. Logging + self-improvement loop

### Per-run artifacts

**`runs/<ISO>_<slug>/manifest.json`**
```json
{
  "run_id": "2026-05-29T14-22-03_da-nang",
  "started_at": "...", "ended_at": "...",
  "inputs": {"destination": "Da Nang", "dates_start": "...", "dates_end": "...", "passport": "PH"},
  "model": "claude-opus-4-7",
  "stages": [{"n": 1, "duration_s": 42, "validate_pass": true, "retries": 0}, ...],
  "geocode_misses": [...], "wiki_misses": [...], "unvalidated_facts": [...],
  "delivered_files": [...],
  "feedback_captured": true|false
}
```

**`runs/<id>/stages.jsonl`** — one JSON object per line. Fields: `ts, stage, event, details`. Events include `stage_start`, `validate_pass`, `validate_fail` (w/ errors), `geocode_miss`, `wiki_miss`, `derive_applied`, `stage_end`.

**`runs/<id>/feedback.md`** — free-form user reply to post-delivery prompt. Captured via `AskUserQuestion`; user may skip.

### Learning consolidation (`--learn`)

`python synthesize.py --learn` is a **manual** command, NOT auto. The CLI itself never calls an LLM (preserves the hard rule). It:
1. Scans `runs/*/feedback.md` modified in last N days (default 30)
2. Concatenates them into `runs/.pending_learnings.md` with run-id headers
3. Prints a one-line instruction to the user: "Open `.pending_learnings.md`, then ask Claude to propose new `learnings.md` entries from it."
4. Claude in-session reads the file, proposes categorised candidates, user accepts/edits/rejects per candidate in chat, Claude writes approved entries to `references/learnings.md` (append-only), Claude deletes the pending file.

Rationale: prevents bad/contradictory feedback from auto-poisoning prompts. Keeps learnings curated. Preserves the "no LLM in synthesize.py" invariant — the LLM work happens in chat, the CLI only collates raw feedback.

### `references/learnings.md` shape

Append-only, sectioned by category:
```markdown
## Tropical SE-Asia
- ...

## Non-tropical EU
- ...

## Pricing
- ...

## Place categories
- ...
```

Every `synth_prompts/0N_*.md` instructs Claude to read `learnings.md` at start of stage. That's the entire learning loop.

## 8. Error handling

| Failure | Where | Behavior |
|---|---|---|
| Malformed JSON in data.json | any stage | `synthesize.py` exits 1 with line+col. Claude re-reads, fixes syntax. |
| Schema validation fail | post-stage | Print all errors. Claude patches → re-run same stage. No auto-fix. |
| Nominatim 429 / network | stage 2 | Sleep 30s + 1 retry → cache miss → log to `geocode_misses.txt` → Claude fills manually. Non-fatal. |
| Wiki precheck 404 | stage 2 | Not an error. Cached. Claude adds `alt_search_query`. |
| Orphan place-key reference in itinerary | stage 4 | Row-invariant fails. List orphans. Claude adds place or fixes typo. |
| v2/v3 day count ≠ v1 | stage 5 | Refuse. Claude regenerates. |
| Ollama fact-validate timeout | final | Non-blocking. Log to `unvalidated.md`. Continue. |
| Renderer error after handoff | run_all.py | Out of scope. Existing handling stands. |

**Principle:** every degraded path leaves a file artifact Claude can read on next pass. No silent fallbacks.

## 9. Testing

### Fixtures
- `trips/da-nang/data.json` — golden, 420 lines hand-authored, PH→VN tropical
- `trips/manila/data.json` — golden, 2349 lines hand-authored, PH domestic tropical
- `trips/_test/lisbon/` — NEW non-tropical EU cross-validation (cold synth; under `_test/` to avoid mixing with real trip outputs; `_test/` added to .gitignore)
- `trips/_test/tokyo/` — NEW Asian non-tropical, multi-lang place names (deferred if time-boxed)

### Layers

1. **Unit (pytest)** at `.claude/skills/itinerary-builder/scripts/tests/`
   - `test_schema_check.py`: known-bad variants → expected error messages
   - `test_geocode.py`: mock Nominatim → cache write/read/hit/miss + 429 retry
   - `test_wiki_precheck.py`: mock requests → 200/404
   - `test_stage_runner.py`: per-stage hooks fire correct validators
   - `test_run_logger.py`: manifest + jsonl event flow

2. **Integration (golden re-validation)**
   - `synthesize.py --slug da-nang --stage final` on existing fixture → must pass
   - Same on manila → must pass
   - Locks back-compat (existing `*_vnd → *_local` `_pick()` shim covered)

3. **End-to-end (manual)**
   - Cold synthesize Da Nang via skill flow. Compare to hand-authored: places count, time-row count per day, all 3 variants, line count within ±30%.
   - Run full `run_all.py` → 14 sheets + Word doc.
   - Repeat Lisbon (cross-climate sanity).

4. **Schema regression (pre-commit)**
   - `pytest scripts/tests/ && python synthesize.py --slug da-nang --stage final && python synthesize.py --slug manila --stage final` runs before any commit touching schema or libs.

### Ollama use during build
- `deepseek-pro` second_opinion on each `synth_prompts/0N_*.md` draft before commit
- `deepseek-flash` reviews each new `lib/*.py`
- `glm` or `minimax` cross-checks fact-validation prompts

## 10. Work plan (waves + subagent split)

**Wave 0 — planning baseline** (main agent, serial) — this spec doc + writing-plans output.

**Wave 1 — primitives** (parallel, 3× `developer` subagents)
- W1.A `lib/schema_check.py` + tests
- W1.B `lib/geocode.py` + tests
- W1.C `lib/wiki_precheck.py` + tests

**Wave 2 — harness + CLI** (serial, 1× `developer`, depends on W1)
- W2.1 `lib/stage_runner.py`
- W2.2 `scripts/synthesize.py`
- W2.3 `lib/run_logger.py`

**Wave 3 — synth prompt templates** (parallel, 6× `developer`/`technical-writer`)
- W3.1–W3.6 one per `synth_prompts/0N_*.md`. Each runs `deepseek-pro` second-opinion pre-commit.

**Wave 4 — pipeline integration** (serial, main agent)
- W4.1 Update `SKILL.md` Phase 1 Path B
- W4.2 Update `references/workflow.md` Phase 1 + add Phase 10.5 (feedback capture)
- W4.3 Seed `references/learnings.md`
- W4.4 Add `--learn` subcommand to `synthesize.py`

**Wave 5 — validation** (parallel, 3× `developer` + 1× `quality-reviewer`)
- W5.A Integration: `--stage final` on da-nang fixture
- W5.B Integration: `--stage final` on manila fixture
- W5.C Cross-climate cold synth: Lisbon stages 1–6 + final
- W5.D `quality-reviewer` agent reviews full diff

**Wave 6 — second-opinion gate** (parallel, `second-opinion` agent)
- Multi-model review (`deepseek-pro` + `glm` + `minimax`) on new `lib/*.py` + synth_prompts. Findings → fix list.

### Cut points if time-boxed
- Drop W6 (nice-to-have)
- Drop W5.C (defer to real user request)
- Drop W4.4 (`--learn` can be hand-curated initially)

## 11. Open follow-ups (post-v1)
- Synthesize-from-3-word free-form prompt
- Multi-pax mixed-passport handling
- Save-as-template (Bali → Tokyo derive)
- Auto-rebuild on schema migration
- CI hook: pre-push runs full pytest + integration suite

## 12. Constraints + gotchas
- Python 3.10+ (tested 3.14 Windows 11)
- New deps: `jsonschema`, `requests` (for Nominatim + Wiki precheck). Add to skill `requirements.txt` or inline `pip install` note.
- Nominatim requires `User-Agent` header.
- Wikipedia REST 404 rate ~30% for small venues per existing fetch_images experience — `alt_search_query` is the escape hatch.
- `build_workbook.py` `_pick()` helper handles legacy `*_vnd` fields — synthesizer emits `*_local` (new schema).
- Skill description ≤1024 chars (Claude Code limit) — keep updates compact.
- Do NOT rewrite renderers, migrate legacy fixture field names, or change `run_all.py` CLI signature.

## 13. Caveman mode note
Session built under caveman mode (full). Code, commits, prompts, and this spec written in normal prose per skill rules. Chat responses caveman-terse.

---

**Approval:** Design sections 1–5 approved by user 2026-05-29. Awaiting spec-file review before invoking writing-plans.
