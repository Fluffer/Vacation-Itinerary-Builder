# Itinerary Synthesizer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a staged in-session LLM-driven synthesizer to the `itinerary-builder` skill that produces a fully-populated, schema-valid `trips/<slug>/data.json` from `destination + dates + passport`, with per-run logging and user-feedback-driven self-improvement.

**Architecture:** Six sequential authoring stages (metadata → places → hotels/pricing/budget → v1 → v2/v3 → ancillary) executed by Claude in-session. A thin Python CLI (`synthesize.py`) provides validators, helpers (geocode, wiki precheck), auto-derivers, and a run-logger between stages. **No LLM is called from `synthesize.py`.** Renderers are untouched.

**Tech Stack:** Python 3.10+, `jsonschema`, `requests`, `pytest`. Existing deps: `python-docx`, `openpyxl`, `Pillow`, `staticmap`. Ollama models available during build/test (deepseek-pro, glm, minimax) but not at runtime.

**Reference spec:** [docs/superpowers/specs/2026-05-29-itinerary-synthesizer-design.md](../specs/2026-05-29-itinerary-synthesizer-design.md)

---

## File structure (final state)

**Created:**

```
.claude/skills/itinerary-builder/
├── references/
│   ├── learnings.md                           NEW seed, empty sections
│   └── synth_prompts/                         NEW dir
│       ├── 01_metadata_visa.md
│       ├── 02_places.md
│       ├── 03_hotels_pricing_budget.md
│       ├── 04_v1_itinerary.md
│       ├── 05_v2_v3_derive.md
│       └── 06_ancillary.md
├── scripts/
│   ├── synthesize.py                          NEW CLI orchestrator
│   ├── lib/
│   │   ├── schema_check.py                    NEW
│   │   ├── geocode.py                         NEW
│   │   ├── wiki_precheck.py                   NEW
│   │   ├── stage_runner.py                    NEW
│   │   └── run_logger.py                      NEW
│   └── tests/                                 NEW
│       ├── __init__.py
│       ├── conftest.py
│       ├── test_schema_check.py
│       ├── test_geocode.py
│       ├── test_wiki_precheck.py
│       ├── test_stage_runner.py
│       ├── test_run_logger.py
│       └── test_synthesize_cli.py
└── runs/                                      NEW (gitignored)
    └── .gitkeep
```

**Modified:**

- `.claude/skills/itinerary-builder/SKILL.md` — Phase 1 Path B section + dep list
- `.claude/skills/itinerary-builder/references/workflow.md` — Phase 1 staged-synth + new Phase 10.5 (feedback capture)
- `.gitignore` (project root) — add `runs/`, `trips/_test/`, `.cache/`, `__pycache__/`
- `.claude/skills/itinerary-builder/requirements.txt` — add `jsonschema`, `requests`, `pytest` (create if missing)

**File responsibilities:**

| File | Single responsibility |
|---|---|
| `lib/schema_check.py` | Validate a data.json dict against the JSON Schema; return list of human-readable errors. |
| `lib/geocode.py` | Resolve `(name, area, country) → (lat, lon)` via Nominatim with disk cache + rate-limit + retry. |
| `lib/wiki_precheck.py` | Probe Wikipedia REST for a title; cached hit/miss result. |
| `lib/stage_runner.py` | Per-stage dispatch: load data.json, run stage-specific validators + auto-derivers, write back. |
| `lib/run_logger.py` | Per-run manifest + jsonl event log + snapshot + feedback capture. |
| `scripts/synthesize.py` | Thin CLI: `--slug <s> --stage <1-6|final|learn>` → dispatches to libs. No LLM calls. |
| `references/synth_prompts/0N_*.md` | Stage-N authoring prompt template Claude reads in-session. |
| `references/learnings.md` | Curated, append-only lessons from prior runs, loaded into every stage prompt. |

---

## Task 0: Repository init + dependency baseline

**Files:**
- Modify (or create): `.gitignore` at `C:/Dev/Active/itinerary-builder/.gitignore`
- Create: `.claude/skills/itinerary-builder/requirements.txt`
- Create: `.claude/skills/itinerary-builder/scripts/tests/__init__.py` (empty)
- Create: `.claude/skills/itinerary-builder/scripts/tests/conftest.py`

This task is serial — it bootstraps the workspace. All other tasks depend on it.

- [ ] **Step 1: Init git repo if missing**

```bash
cd C:/Dev/Active/itinerary-builder
if [ ! -d .git ]; then git init && git add -A && git commit -m "chore: snapshot pre-synthesizer state"; fi
```

Expected: either a fresh repo with one snapshot commit, or `git status` already shows a working repo.

- [ ] **Step 2: Create / update `.gitignore`**

Append (idempotent — check before adding) the following block to `.gitignore`:

```
# Synthesizer
.claude/skills/itinerary-builder/runs/*
!.claude/skills/itinerary-builder/runs/.gitkeep
trips/_test/
trips/*/.cache/
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 3: Create `requirements.txt`**

Write to `.claude/skills/itinerary-builder/requirements.txt`:

```
python-docx>=1.1
openpyxl>=3.1
Pillow>=10
staticmap>=0.5
jsonschema>=4.20
requests>=2.31
pytest>=8.0
```

- [ ] **Step 4: Install deps**

```bash
pip install -r .claude/skills/itinerary-builder/requirements.txt
```

Expected: all installs succeed.

- [ ] **Step 5: Create test scaffold**

Write `.claude/skills/itinerary-builder/scripts/tests/__init__.py` (empty file).

Write `.claude/skills/itinerary-builder/scripts/tests/conftest.py`:

```python
"""Shared pytest fixtures for the itinerary-builder synthesizer."""
import json
import os
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture
def tmp_trip(tmp_path: Path) -> Path:
    """Create a tmp trips/<slug> directory and return its path."""
    slug_dir = tmp_path / "trips" / "test-slug"
    slug_dir.mkdir(parents=True)
    (slug_dir / ".cache").mkdir()
    return slug_dir


@pytest.fixture
def minimal_data() -> dict:
    """Minimal data.json shape passing partial schema validation."""
    return {
        "slug": "test-slug",
        "metadata": {
            "dates_start": "2026-08-14",
            "dates_end": "2026-08-18",
            "origin": "Manila",
            "destination": "Da Nang",
            "passport": "PH",
            "pax": 2,
            "base_hotel_area": "My Khe Beach",
            "currency_code": "VND",
        },
        "itinerary": {},
        "places": [],
    }


@pytest.fixture
def schema_path() -> Path:
    """Absolute path to the trip_data schema."""
    return SCRIPTS_DIR.parent / "templates" / "trip_data.schema.json"
```

- [ ] **Step 6: Verify pytest discovers the scaffold**

```bash
cd C:/Dev/Active/itinerary-builder
pytest .claude/skills/itinerary-builder/scripts/tests/ -v
```

Expected: `no tests ran` (no test files yet) with no errors.

- [ ] **Step 7: Commit**

```bash
git add .gitignore .claude/skills/itinerary-builder/requirements.txt .claude/skills/itinerary-builder/scripts/tests/
git commit -m "chore(synth): scaffold tests + dependencies"
```

---

## Wave 1 — Primitives (Tasks 1, 2, 3 can run in parallel)

### Task 1: `lib/schema_check.py`

**Files:**
- Create: `.claude/skills/itinerary-builder/scripts/lib/schema_check.py`
- Test: `.claude/skills/itinerary-builder/scripts/tests/test_schema_check.py`

- [ ] **Step 1: Write the failing tests**

Write `.claude/skills/itinerary-builder/scripts/tests/test_schema_check.py`:

```python
import json
from pathlib import Path

import pytest

from lib.schema_check import validate, validate_file


def test_partial_accepts_minimal(minimal_data):
    errors = validate(minimal_data, partial=True)
    assert errors == []


def test_strict_rejects_missing_required(minimal_data):
    errors = validate(minimal_data, partial=False)
    # Strict mode passes for the minimal shape (only top-level required is slug/metadata/itinerary/places).
    assert errors == []


def test_strict_rejects_missing_top_level(minimal_data):
    del minimal_data["places"]
    errors = validate(minimal_data, partial=False)
    assert any("places" in e for e in errors)


def test_partial_allows_missing_top_level(minimal_data):
    del minimal_data["places"]
    errors = validate(minimal_data, partial=True)
    assert errors == []


def test_rejects_wrong_enum(minimal_data):
    minimal_data["places"].append({"key": "x", "name": "X", "category": "not_a_real_category"})
    errors = validate(minimal_data, partial=True)
    assert any("category" in e for e in errors)


def test_rejects_wrong_type(minimal_data):
    minimal_data["metadata"]["pax"] = "not-an-int"
    errors = validate(minimal_data, partial=True)
    assert any("pax" in e for e in errors)


def test_validate_file_reads_disk(tmp_trip, minimal_data):
    p = tmp_trip / "data.json"
    p.write_text(json.dumps(minimal_data), encoding="utf-8")
    errors = validate_file(p, partial=True)
    assert errors == []


def test_error_strings_are_path_message_format(minimal_data):
    minimal_data["metadata"]["pax"] = "x"
    errors = validate(minimal_data, partial=True)
    # Format: "path: message"
    assert any(":" in e for e in errors)
```

- [ ] **Step 2: Run tests, verify FAIL**

```bash
pytest .claude/skills/itinerary-builder/scripts/tests/test_schema_check.py -v
```

Expected: `ImportError` / `ModuleNotFoundError` for `lib.schema_check`.

- [ ] **Step 3: Create `lib/__init__.py` if missing**

```bash
touch .claude/skills/itinerary-builder/scripts/lib/__init__.py
```

(Note: file likely already exists alongside `common.py`. If it does, skip.)

- [ ] **Step 4: Implement `lib/schema_check.py`**

Write `.claude/skills/itinerary-builder/scripts/lib/schema_check.py`:

```python
"""JSON Schema validator for trip data.json."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from jsonschema import Draft7Validator

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "templates" / "trip_data.schema.json"


def _load_schema() -> dict:
    with _SCHEMA_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def _format_error(err) -> str:
    # err.absolute_path is a deque of path segments.
    path = "/".join(str(p) for p in err.absolute_path) or "<root>"
    return f"{path}: {err.message}"


def validate(data: dict, partial: bool = False) -> list[str]:
    """Validate `data` against the schema.

    partial=True drops the top-level `required` enforcement so callers can
    validate mid-stage shapes where not all blocks are populated yet.
    Returns a list of human-readable error strings ("path: message"); empty = pass.
    """
    schema = _load_schema()
    if partial:
        schema = {**schema}
        schema.pop("required", None)
    validator = Draft7Validator(schema)
    return [_format_error(e) for e in validator.iter_errors(data)]


def validate_file(path: str | Path, partial: bool = False) -> list[str]:
    """Convenience: validate a data.json on disk."""
    p = Path(path)
    with p.open(encoding="utf-8") as fh:
        data = json.load(fh)
    return validate(data, partial=partial)


def main(argv: Iterable[str] | None = None) -> int:
    """CLI entry: python -m lib.schema_check <path> [--strict]"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("--strict", action="store_true", help="Disable partial mode")
    args = parser.parse_args(argv)
    errors = validate_file(args.path, partial=not args.strict)
    if errors:
        for e in errors:
            print(e)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run tests, verify PASS**

```bash
pytest .claude/skills/itinerary-builder/scripts/tests/test_schema_check.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 6: Smoke against real fixture**

```bash
python .claude/skills/itinerary-builder/scripts/lib/schema_check.py trips/manila/data.json
```

Expected: prints `OK` (or specific errors — if errors, the legacy fixture has stale fields; investigate before committing).

- [ ] **Step 7: Commit**

```bash
git add .claude/skills/itinerary-builder/scripts/lib/schema_check.py .claude/skills/itinerary-builder/scripts/lib/__init__.py .claude/skills/itinerary-builder/scripts/tests/test_schema_check.py
git commit -m "feat(synth): add lib.schema_check for staged validation"
```

---

### Task 2: `lib/geocode.py`

**Files:**
- Create: `.claude/skills/itinerary-builder/scripts/lib/geocode.py`
- Test: `.claude/skills/itinerary-builder/scripts/tests/test_geocode.py`

**Parallelisable with Tasks 1 and 3.**

- [ ] **Step 1: Write the failing tests**

Write `.claude/skills/itinerary-builder/scripts/tests/test_geocode.py`:

```python
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from lib.geocode import Geocoder


def _mk_response(payload, status=200):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = payload
    r.raise_for_status.return_value = None
    return r


def test_geocode_hit_writes_cache(tmp_trip):
    cache = tmp_trip / ".cache" / "geocode.json"
    payload = [{"lat": "16.0544", "lon": "108.2022"}]
    with patch("lib.geocode.requests.get", return_value=_mk_response(payload)) as m:
        gc = Geocoder(cache_path=cache, sleep_s=0)
        lat, lon = gc.geocode("Dragon Bridge", "Da Nang", "Vietnam")
    assert (lat, lon) == (16.0544, 108.2022)
    assert m.call_count == 1
    stored = json.loads(cache.read_text(encoding="utf-8"))
    assert "Dragon Bridge|Da Nang|Vietnam" in stored


def test_geocode_uses_cache_on_second_call(tmp_trip):
    cache = tmp_trip / ".cache" / "geocode.json"
    cache.write_text(json.dumps({"X|A|C": [1.0, 2.0]}), encoding="utf-8")
    with patch("lib.geocode.requests.get") as m:
        gc = Geocoder(cache_path=cache, sleep_s=0)
        lat, lon = gc.geocode("X", "A", "C")
    assert (lat, lon) == (1.0, 2.0)
    assert m.call_count == 0


def test_geocode_miss_returns_none(tmp_trip):
    cache = tmp_trip / ".cache" / "geocode.json"
    with patch("lib.geocode.requests.get", return_value=_mk_response([])):
        gc = Geocoder(cache_path=cache, sleep_s=0)
        result = gc.geocode("Nowhere", "Nowhere", "Nowhere")
    assert result is None
    stored = json.loads(cache.read_text(encoding="utf-8"))
    assert stored["Nowhere|Nowhere|Nowhere"] is None


def test_geocode_429_retries_then_gives_up(tmp_trip):
    cache = tmp_trip / ".cache" / "geocode.json"
    resp_429 = _mk_response([], status=429)
    with patch("lib.geocode.requests.get", return_value=resp_429) as m, \
         patch("lib.geocode.time.sleep") as sleep_mock:
        gc = Geocoder(cache_path=cache, sleep_s=0, retry_backoff_s=0.01)
        result = gc.geocode("X", "Y", "Z")
    assert result is None
    assert m.call_count == 2  # initial + 1 retry
    assert sleep_mock.called


def test_geocode_batch_fills_in_place(tmp_trip):
    cache = tmp_trip / ".cache" / "geocode.json"
    payload = [{"lat": "10.0", "lon": "20.0"}]
    places = [
        {"key": "a", "name": "A", "area": "X"},  # no lat/lon
        {"key": "b", "name": "B", "area": "Y", "lat": 1.0, "lon": 2.0},  # already has
    ]
    with patch("lib.geocode.requests.get", return_value=_mk_response(payload)):
        gc = Geocoder(cache_path=cache, sleep_s=0)
        misses = gc.geocode_batch(places, country="Vietnam")
    assert places[0]["lat"] == 10.0 and places[0]["lon"] == 20.0
    assert places[1]["lat"] == 1.0  # unchanged
    assert misses == 0


def test_geocode_batch_counts_misses(tmp_trip):
    cache = tmp_trip / ".cache" / "geocode.json"
    with patch("lib.geocode.requests.get", return_value=_mk_response([])):
        gc = Geocoder(cache_path=cache, sleep_s=0)
        places = [{"key": "a", "name": "A", "area": "X"}]
        misses = gc.geocode_batch(places, country="Nowhere")
    assert misses == 1
    assert "lat" not in places[0]
```

- [ ] **Step 2: Run tests, verify FAIL (import error)**

```bash
pytest .claude/skills/itinerary-builder/scripts/tests/test_geocode.py -v
```

Expected: `ModuleNotFoundError: No module named 'lib.geocode'`.

- [ ] **Step 3: Implement `lib/geocode.py`**

Write `.claude/skills/itinerary-builder/scripts/lib/geocode.py`:

```python
"""Nominatim geocoder with per-trip disk cache + rate-limit handling."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Iterable

import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "itinerary-builder/1.0 (synthesizer)"


class Geocoder:
    def __init__(
        self,
        cache_path: Path,
        sleep_s: float = 1.1,
        timeout_s: float = 5.0,
        retry_backoff_s: float = 30.0,
    ) -> None:
        self.cache_path = Path(cache_path)
        self.sleep_s = sleep_s
        self.timeout_s = timeout_s
        self.retry_backoff_s = retry_backoff_s
        self._cache: dict[str, tuple[float, float] | None] = self._load_cache()

    def _load_cache(self) -> dict:
        if not self.cache_path.exists():
            return {}
        try:
            raw = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
        return {k: (tuple(v) if isinstance(v, list) else None) for k, v in raw.items()}

    def _save_cache(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        serialisable = {k: (list(v) if v is not None else None) for k, v in self._cache.items()}
        self.cache_path.write_text(json.dumps(serialisable, indent=2), encoding="utf-8")

    @staticmethod
    def _key(name: str, area: str, country: str) -> str:
        return f"{name}|{area}|{country}"

    def geocode(self, name: str, area: str, country: str) -> tuple[float, float] | None:
        key = self._key(name, area, country)
        if key in self._cache:
            return self._cache[key]

        query = ", ".join(p for p in (name, area, country) if p)
        params = {"q": query, "format": "json", "limit": 1}
        headers = {"User-Agent": USER_AGENT}

        for attempt in (0, 1):  # initial + 1 retry on 429
            try:
                resp = requests.get(
                    NOMINATIM_URL, params=params, headers=headers, timeout=self.timeout_s
                )
            except requests.RequestException:
                self._cache[key] = None
                self._save_cache()
                return None

            if resp.status_code == 429 and attempt == 0:
                time.sleep(self.retry_backoff_s)
                continue
            if resp.status_code != 200:
                self._cache[key] = None
                self._save_cache()
                return None

            data = resp.json()
            if not data:
                self._cache[key] = None
                self._save_cache()
                return None

            lat = float(data[0]["lat"])
            lon = float(data[0]["lon"])
            self._cache[key] = (lat, lon)
            self._save_cache()
            if self.sleep_s > 0:
                time.sleep(self.sleep_s)
            return (lat, lon)

        # all attempts exhausted on 429
        self._cache[key] = None
        self._save_cache()
        return None

    def geocode_batch(self, places: Iterable[dict], country: str) -> int:
        """Fill lat/lon in-place for any place missing them. Returns miss count."""
        misses = 0
        for p in places:
            if p.get("lat") is not None and p.get("lon") is not None:
                continue
            result = self.geocode(p.get("name", ""), p.get("area", ""), country)
            if result is None:
                misses += 1
            else:
                p["lat"], p["lon"] = result
        return misses
```

- [ ] **Step 4: Run tests, verify PASS**

```bash
pytest .claude/skills/itinerary-builder/scripts/tests/test_geocode.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/itinerary-builder/scripts/lib/geocode.py .claude/skills/itinerary-builder/scripts/tests/test_geocode.py
git commit -m "feat(synth): add lib.geocode (Nominatim + cache + 429 retry)"
```

---

### Task 3: `lib/wiki_precheck.py`

**Files:**
- Create: `.claude/skills/itinerary-builder/scripts/lib/wiki_precheck.py`
- Test: `.claude/skills/itinerary-builder/scripts/tests/test_wiki_precheck.py`

**Parallelisable with Tasks 1 and 2.**

- [ ] **Step 1: Write the failing tests**

Write `.claude/skills/itinerary-builder/scripts/tests/test_wiki_precheck.py`:

```python
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from lib.wiki_precheck import WikiPrechecker


def _mk(status: int):
    r = MagicMock()
    r.status_code = status
    return r


def test_hit_returns_true(tmp_trip):
    cache = tmp_trip / ".cache" / "wiki.json"
    with patch("lib.wiki_precheck.requests.get", return_value=_mk(200)):
        pc = WikiPrechecker(cache_path=cache, sleep_s=0)
        assert pc.precheck("Dragon_Bridge") is True
    stored = json.loads(cache.read_text(encoding="utf-8"))
    assert stored["Dragon_Bridge"] is True


def test_miss_returns_false(tmp_trip):
    cache = tmp_trip / ".cache" / "wiki.json"
    with patch("lib.wiki_precheck.requests.get", return_value=_mk(404)):
        pc = WikiPrechecker(cache_path=cache, sleep_s=0)
        assert pc.precheck("Nope_Place") is False
    stored = json.loads(cache.read_text(encoding="utf-8"))
    assert stored["Nope_Place"] is False


def test_uses_cache(tmp_trip):
    cache = tmp_trip / ".cache" / "wiki.json"
    cache.write_text(json.dumps({"X": True}), encoding="utf-8")
    with patch("lib.wiki_precheck.requests.get") as m:
        pc = WikiPrechecker(cache_path=cache, sleep_s=0)
        assert pc.precheck("X") is True
    assert m.call_count == 0


def test_precheck_places_returns_per_entry(tmp_trip):
    cache = tmp_trip / ".cache" / "wiki.json"
    def side_effect(url, **kw):
        return _mk(200 if "Bridge" in url else 404)
    with patch("lib.wiki_precheck.requests.get", side_effect=side_effect):
        pc = WikiPrechecker(cache_path=cache, sleep_s=0)
        results = pc.precheck_places([
            {"key": "a", "wiki_title": "Dragon_Bridge"},
            {"key": "b", "wiki_title": "Nope"},
            {"key": "c"},  # no wiki_title — skipped
        ])
    keys = {r["key"]: r["hit"] for r in results}
    assert keys == {"a": True, "b": False, "c": None}
```

- [ ] **Step 2: Run tests, verify FAIL**

```bash
pytest .claude/skills/itinerary-builder/scripts/tests/test_wiki_precheck.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `lib/wiki_precheck.py`**

Write `.claude/skills/itinerary-builder/scripts/lib/wiki_precheck.py`:

```python
"""Wikipedia REST page-summary probe with disk cache."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Iterable

import requests

WIKI_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/"
USER_AGENT = "itinerary-builder/1.0 (synthesizer)"


class WikiPrechecker:
    def __init__(
        self,
        cache_path: Path,
        sleep_s: float = 0.1,
        timeout_s: float = 5.0,
    ) -> None:
        self.cache_path = Path(cache_path)
        self.sleep_s = sleep_s
        self.timeout_s = timeout_s
        self._cache: dict[str, bool] = self._load_cache()

    def _load_cache(self) -> dict[str, bool]:
        if not self.cache_path.exists():
            return {}
        try:
            return json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_cache(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(self._cache, indent=2), encoding="utf-8")

    def precheck(self, title: str) -> bool:
        if title in self._cache:
            return self._cache[title]
        url = WIKI_URL + title
        headers = {"User-Agent": USER_AGENT}
        try:
            resp = requests.get(url, headers=headers, timeout=self.timeout_s)
        except requests.RequestException:
            self._cache[title] = False
            self._save_cache()
            return False
        hit = resp.status_code == 200
        self._cache[title] = hit
        self._save_cache()
        if self.sleep_s > 0:
            time.sleep(self.sleep_s)
        return hit

    def precheck_places(self, places: Iterable[dict]) -> list[dict]:
        """For each place with `wiki_title`, probe and return result list.
        Entries without `wiki_title` get `hit=None`.
        """
        out = []
        for p in places:
            title = p.get("wiki_title")
            if not title:
                out.append({"key": p.get("key"), "wiki_title": None, "hit": None})
                continue
            out.append({"key": p.get("key"), "wiki_title": title, "hit": self.precheck(title)})
        return out
```

- [ ] **Step 4: Run tests, verify PASS**

```bash
pytest .claude/skills/itinerary-builder/scripts/tests/test_wiki_precheck.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/itinerary-builder/scripts/lib/wiki_precheck.py .claude/skills/itinerary-builder/scripts/tests/test_wiki_precheck.py
git commit -m "feat(synth): add lib.wiki_precheck"
```

---

## Wave 2 — Harness + CLI (Tasks 4, 5, 6 are sequential)

### Task 4: `lib/run_logger.py`

**Files:**
- Create: `.claude/skills/itinerary-builder/scripts/lib/run_logger.py`
- Test: `.claude/skills/itinerary-builder/scripts/tests/test_run_logger.py`

**Depends on:** Task 0.

- [ ] **Step 1: Write the failing tests**

Write `.claude/skills/itinerary-builder/scripts/tests/test_run_logger.py`:

```python
import json
from pathlib import Path

import pytest

from lib.run_logger import RunLogger


def test_start_creates_run_dir(tmp_path):
    runs_root = tmp_path / "runs"
    with RunLogger(slug="da-nang", runs_root=runs_root,
                   inputs={"destination": "Da Nang", "passport": "PH"}) as rl:
        run_dir = rl.run_dir
        assert run_dir.exists()
        assert (run_dir / "manifest.json").exists()
        assert (run_dir / "stages.jsonl").exists()
    # On close, manifest finalised with ended_at
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert "ended_at" in manifest
    assert manifest["inputs"]["destination"] == "Da Nang"


def test_log_event_appends_to_jsonl(tmp_path):
    runs_root = tmp_path / "runs"
    with RunLogger(slug="x", runs_root=runs_root, inputs={}) as rl:
        rl.log_event(stage=1, event="stage_start")
        rl.log_event(stage=1, event="validate_pass", details={"errors": []})
    lines = (rl.run_dir / "stages.jsonl").read_text(encoding="utf-8").strip().splitlines()
    events = [json.loads(line) for line in lines]
    assert len(events) == 2
    assert events[0]["event"] == "stage_start"
    assert events[1]["details"]["errors"] == []


def test_snapshot_data_copies_file(tmp_path):
    runs_root = tmp_path / "runs"
    src = tmp_path / "data.json"
    src.write_text('{"slug": "x"}', encoding="utf-8")
    with RunLogger(slug="x", runs_root=runs_root, inputs={}) as rl:
        rl.snapshot_data(src)
        snap = rl.run_dir / "data.snapshot.json"
        assert snap.exists()
        assert json.loads(snap.read_text(encoding="utf-8"))["slug"] == "x"


def test_capture_feedback_writes_file(tmp_path):
    runs_root = tmp_path / "runs"
    with RunLogger(slug="x", runs_root=runs_root, inputs={}) as rl:
        rl.capture_feedback("v1 had too few food places\nDay 3 too packed")
        fb = rl.run_dir / "feedback.md"
        assert fb.exists()
        assert "Day 3" in fb.read_text(encoding="utf-8")
    manifest = json.loads((rl.run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["feedback_captured"] is True


def test_no_feedback_marks_false(tmp_path):
    runs_root = tmp_path / "runs"
    with RunLogger(slug="x", runs_root=runs_root, inputs={}) as rl:
        pass  # never call capture_feedback
    manifest = json.loads((rl.run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["feedback_captured"] is False


def test_resume_existing_run(tmp_path):
    runs_root = tmp_path / "runs"
    # Initial run
    with RunLogger(slug="x", runs_root=runs_root, inputs={"a": 1}) as rl:
        run_id = rl.run_id
        rl.log_event(stage=1, event="stage_start")
    # Resume by run_id
    with RunLogger.resume(slug="x", run_id=run_id, runs_root=runs_root) as rl:
        rl.log_event(stage=2, event="stage_start")
    lines = (runs_root / run_id).joinpath("stages.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
```

- [ ] **Step 2: Run tests, verify FAIL**

```bash
pytest .claude/skills/itinerary-builder/scripts/tests/test_run_logger.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `lib/run_logger.py`**

Write `.claude/skills/itinerary-builder/scripts/lib/run_logger.py`:

```python
"""Per-run logger: manifest.json + stages.jsonl + snapshot + feedback."""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")


class RunLogger:
    def __init__(
        self,
        slug: str,
        runs_root: Path,
        inputs: dict,
        run_id: str | None = None,
        model: str = "claude-opus-4-7",
    ) -> None:
        self.slug = slug
        self.runs_root = Path(runs_root)
        self.inputs = inputs
        self.model = model
        if run_id is None:
            run_id = f"{_utc_now_iso()}_{slug}"
        self.run_id = run_id
        self.run_dir = self.runs_root / run_id
        self._opened_fresh = not self.run_dir.exists()

    @classmethod
    def resume(cls, slug: str, run_id: str, runs_root: Path) -> "RunLogger":
        rl = cls(slug=slug, runs_root=runs_root, inputs={}, run_id=run_id)
        if not rl.run_dir.exists():
            raise FileNotFoundError(f"No run at {rl.run_dir}")
        # Load inputs from existing manifest so resume is faithful
        manifest = json.loads((rl.run_dir / "manifest.json").read_text(encoding="utf-8"))
        rl.inputs = manifest.get("inputs", {})
        rl._opened_fresh = False
        return rl

    def __enter__(self) -> "RunLogger":
        self.run_dir.mkdir(parents=True, exist_ok=True)
        if self._opened_fresh:
            manifest = {
                "run_id": self.run_id,
                "started_at": _utc_now_iso(),
                "ended_at": None,
                "inputs": self.inputs,
                "model": self.model,
                "feedback_captured": False,
                "delivered_files": [],
            }
            (self.run_dir / "manifest.json").write_text(
                json.dumps(manifest, indent=2), encoding="utf-8"
            )
            (self.run_dir / "stages.jsonl").write_text("", encoding="utf-8")
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        manifest_path = self.run_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["ended_at"] = _utc_now_iso()
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    def log_event(self, stage: int | str, event: str, details: dict | None = None) -> None:
        line = {
            "ts": _utc_now_iso(),
            "stage": stage,
            "event": event,
            "details": details or {},
        }
        with (self.run_dir / "stages.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(line) + "\n")

    def snapshot_data(self, data_path: Path) -> None:
        shutil.copyfile(data_path, self.run_dir / "data.snapshot.json")

    def capture_feedback(self, text: str) -> None:
        (self.run_dir / "feedback.md").write_text(text, encoding="utf-8")
        self._update_manifest({"feedback_captured": True})

    def record_delivery(self, files: list[str]) -> None:
        self._update_manifest({"delivered_files": files})

    def _update_manifest(self, patch: dict[str, Any]) -> None:
        path = self.run_dir / "manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest.update(patch)
        path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
```

- [ ] **Step 4: Run tests, verify PASS**

```bash
pytest .claude/skills/itinerary-builder/scripts/tests/test_run_logger.py -v
```

Expected: 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/itinerary-builder/scripts/lib/run_logger.py .claude/skills/itinerary-builder/scripts/tests/test_run_logger.py
git commit -m "feat(synth): add lib.run_logger (manifest + jsonl + snapshot + feedback)"
```

---

### Task 5: `lib/stage_runner.py`

**Files:**
- Create: `.claude/skills/itinerary-builder/scripts/lib/stage_runner.py`
- Test: `.claude/skills/itinerary-builder/scripts/tests/test_stage_runner.py`

**Depends on:** Tasks 1, 2, 3, 4.

- [ ] **Step 1: Write the failing tests**

Write `.claude/skills/itinerary-builder/scripts/tests/test_stage_runner.py`:

```python
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from lib.stage_runner import run_stage, final_validate, StageResult


def _write_data(slug_dir: Path, data: dict) -> Path:
    p = slug_dir / "data.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_stage_1_passes_with_metadata_and_visa(tmp_trip, minimal_data):
    minimal_data["visa"] = {"rule": "Visa-exempt 21 days"}
    _write_data(tmp_trip, minimal_data)
    result = run_stage(slug_dir=tmp_trip, stage_num=1)
    assert isinstance(result, StageResult)
    assert result.passed is True
    assert result.errors == []


def test_stage_1_fails_when_metadata_missing(tmp_trip, minimal_data):
    del minimal_data["metadata"]["pax"]
    _write_data(tmp_trip, minimal_data)
    result = run_stage(slug_dir=tmp_trip, stage_num=1)
    assert result.passed is False
    assert any("pax" in e for e in result.errors)


def test_stage_2_runs_geocode_and_wiki(tmp_trip, minimal_data):
    minimal_data["places"] = [
        {"key": "x", "name": "X", "area": "A", "category": "iconic", "wiki_title": "X_(disambig)"},
    ]
    _write_data(tmp_trip, minimal_data)
    with patch("lib.geocode.requests.get") as gm, \
         patch("lib.wiki_precheck.requests.get") as wm:
        from unittest.mock import MagicMock
        gr = MagicMock(); gr.status_code = 200; gr.json.return_value = [{"lat": "1.0", "lon": "2.0"}]; gr.raise_for_status.return_value = None
        wr = MagicMock(); wr.status_code = 200
        gm.return_value = gr
        wm.return_value = wr
        result = run_stage(slug_dir=tmp_trip, stage_num=2, country="Vietnam")
    data = json.loads((tmp_trip / "data.json").read_text(encoding="utf-8"))
    assert data["places"][0]["lat"] == 1.0
    assert result.passed is True


def test_stage_4_orphan_place_key_fails(tmp_trip, minimal_data):
    minimal_data["places"] = [{"key": "real_place", "name": "Real", "category": "iconic"}]
    minimal_data["itinerary"] = {
        "v1_standard": [{
            "day_label": "Day 1",
            "rows": [{"time": "09:00", "activity": "Visit ghost_place", "place_key": "ghost_place"}],
        }],
    }
    _write_data(tmp_trip, minimal_data)
    result = run_stage(slug_dir=tmp_trip, stage_num=4)
    assert result.passed is False
    assert any("ghost_place" in e for e in result.errors)


def test_stage_5_day_count_mismatch_fails(tmp_trip, minimal_data):
    minimal_data["itinerary"] = {
        "v1_standard": [{"day_label": "D1", "rows": []}, {"day_label": "D2", "rows": []}],
        "v2_relaxed": [{"day_label": "D1", "rows": []}],  # missing D2
        "v3_weather": [{"day_label": "D1", "rows": []}, {"day_label": "D2", "rows": []}],
    }
    _write_data(tmp_trip, minimal_data)
    result = run_stage(slug_dir=tmp_trip, stage_num=5)
    assert result.passed is False
    assert any("day count" in e.lower() or "v2" in e.lower() for e in result.errors)


def test_stage_6_strict_schema_and_derives(tmp_trip, minimal_data):
    minimal_data["places"] = [
        {"key": "p1", "name": "P1", "category": "iconic", "indoor": True,
         "distance_km_from_base": 5.0, "travel_min_from_base": 15, "area": "A"},
    ]
    minimal_data["itinerary"] = {
        "v1_standard": [{"day_label": "Day 1", "rows": []}],
        "v2_relaxed": [{"day_label": "Day 1", "rows": []}],
        "v3_weather": [{"day_label": "Day 1", "rows": []}],
    }
    minimal_data["weather_plan_b"] = {"emit": True, "indoor_bank": []}
    minimal_data["distance_matrix"] = []
    _write_data(tmp_trip, minimal_data)
    result = run_stage(slug_dir=tmp_trip, stage_num=6)
    data = json.loads((tmp_trip / "data.json").read_text(encoding="utf-8"))
    # Auto-derive should have added p1 to indoor_bank and distance_matrix
    assert len(data["weather_plan_b"]["indoor_bank"]) >= 1
    assert len(data["distance_matrix"]) >= 1
    assert result.passed is True


def test_final_validate_calls_strict_schema(tmp_trip, minimal_data):
    minimal_data["itinerary"] = {
        "v1_standard": [{"day_label": "D1", "rows": []}],
        "v2_relaxed": [{"day_label": "D1", "rows": []}],
        "v3_weather": [{"day_label": "D1", "rows": []}],
    }
    _write_data(tmp_trip, minimal_data)
    # final_validate should not fail on the minimal shape (it just calls strict + tries facts)
    result = final_validate(slug_dir=tmp_trip, skip_fact_validate=True)
    assert result.passed is True
```

- [ ] **Step 2: Run tests, verify FAIL**

```bash
pytest .claude/skills/itinerary-builder/scripts/tests/test_stage_runner.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `lib/stage_runner.py`**

Write `.claude/skills/itinerary-builder/scripts/lib/stage_runner.py`:

```python
"""Per-stage validators + auto-derivers + final-validate."""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from lib.schema_check import validate
from lib.geocode import Geocoder
from lib.wiki_precheck import WikiPrechecker

TIME_RE = re.compile(r"^([0-1]?\d|2[0-3]):[0-5]\d$|^.{2,40}$")  # HH:MM or short label


@dataclass
class StageResult:
    passed: bool
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    duration_s: float = 0.0


def _load(slug_dir: Path) -> dict:
    return json.loads((slug_dir / "data.json").read_text(encoding="utf-8"))


def _save(slug_dir: Path, data: dict) -> None:
    (slug_dir / "data.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _cache_path(slug_dir: Path, name: str) -> Path:
    cache_dir = slug_dir / ".cache"
    cache_dir.mkdir(exist_ok=True)
    return cache_dir / name


def _stage_1_metadata_visa(data: dict) -> list[str]:
    return validate(data, partial=True)


def _stage_2_places(data: dict, slug_dir: Path, country: str | None) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    notes: list[str] = []
    if not data.get("places"):
        errors.append("places: must contain at least 1 entry by stage 2")
        return errors, notes

    country = country or data.get("metadata", {}).get("destination", "")
    gc = Geocoder(cache_path=_cache_path(slug_dir, "geocode.json"))
    misses = gc.geocode_batch(data["places"], country=country)
    if misses:
        notes.append(f"geocode misses: {misses}")

    wp = WikiPrechecker(cache_path=_cache_path(slug_dir, "wiki.json"))
    results = wp.precheck_places(data["places"])
    for r in results:
        if r["hit"] is False:
            notes.append(f"wiki miss: {r['wiki_title']} (place key={r['key']}) — add alt_search_query")

    errors.extend(validate(data, partial=True))
    return errors, notes


def _stage_3_hotels_pricing_budget(data: dict) -> list[str]:
    errors: list[str] = []
    if not data.get("hotels"):
        errors.append("hotels: missing")
    if not data.get("activity_pricing"):
        errors.append("activity_pricing: missing")
    if not data.get("budget"):
        errors.append("budget: missing")
    errors.extend(validate(data, partial=True))
    return errors


def _stage_4_v1(data: dict) -> list[str]:
    errors: list[str] = []
    v1 = data.get("itinerary", {}).get("v1_standard")
    if not v1:
        errors.append("itinerary.v1_standard: missing")
        return errors
    place_keys = {p["key"] for p in data.get("places", [])}
    for day_idx, day in enumerate(v1):
        for row_idx, row in enumerate(day.get("rows", [])):
            if "time" not in row:
                errors.append(f"v1_standard[{day_idx}].rows[{row_idx}]: missing time")
            elif not TIME_RE.match(str(row["time"])):
                errors.append(f"v1_standard[{day_idx}].rows[{row_idx}]: bad time format '{row['time']}'")
            pk = row.get("place_key")
            if pk and pk not in place_keys:
                errors.append(f"v1_standard[{day_idx}].rows[{row_idx}]: place_key '{pk}' not in places[]")
    errors.extend(validate(data, partial=True))
    return errors


def _stage_5_v2_v3(data: dict) -> list[str]:
    errors: list[str] = []
    it = data.get("itinerary", {})
    v1, v2, v3 = it.get("v1_standard"), it.get("v2_relaxed"), it.get("v3_weather")
    if not (v1 and v2 and v3):
        errors.append("itinerary: stage 5 requires v1_standard, v2_relaxed, v3_weather all present")
        return errors
    if len(v1) != len(v2):
        errors.append(f"v2_relaxed: day count {len(v2)} does not match v1 day count {len(v1)}")
    if len(v1) != len(v3):
        errors.append(f"v3_weather: day count {len(v3)} does not match v1 day count {len(v1)}")
    errors.extend(validate(data, partial=True))
    return errors


def _stage_6_ancillary_and_derive(data: dict) -> list[str]:
    # Auto-derive distance_matrix
    dm = data.setdefault("distance_matrix", [])
    existing_pairs = {(d.get("from"), d.get("to")) for d in dm}
    base = data.get("metadata", {}).get("base_hotel_area", "Base")
    for p in data.get("places", []):
        if p.get("distance_km_from_base") is None or p.get("travel_min_from_base") is None:
            continue
        pair = (base, p["name"])
        if pair not in existing_pairs:
            dm.append({
                "from": base, "to": p["name"],
                "km": p["distance_km_from_base"], "min": p["travel_min_from_base"],
            })

    # Auto-derive indoor_bank
    wpb = data.setdefault("weather_plan_b", {})
    bank = wpb.setdefault("indoor_bank", [])
    bank_names = {b.get("name") for b in bank}
    for p in data.get("places", []):
        if p.get("indoor") and p.get("name") not in bank_names:
            bank.append({
                "name": p["name"], "area": p.get("area", ""),
                "local_cost": p.get("price_local"),
                "duration": p.get("duration", ""),
                "notes": p.get("description", "")[:200],
            })

    # Strict schema
    return validate(data, partial=False)


def run_stage(slug_dir: Path, stage_num: int, country: str | None = None) -> StageResult:
    start = time.monotonic()
    data = _load(slug_dir)
    errors: list[str] = []
    notes: list[str] = []

    if stage_num == 1:
        errors = _stage_1_metadata_visa(data)
    elif stage_num == 2:
        errors, notes = _stage_2_places(data, slug_dir, country)
    elif stage_num == 3:
        errors = _stage_3_hotels_pricing_budget(data)
    elif stage_num == 4:
        errors = _stage_4_v1(data)
    elif stage_num == 5:
        errors = _stage_5_v2_v3(data)
    elif stage_num == 6:
        errors = _stage_6_ancillary_and_derive(data)
    else:
        return StageResult(passed=False, errors=[f"unknown stage {stage_num}"])

    _save(slug_dir, data)  # persist any mutations (geocode fills, derivations)
    return StageResult(
        passed=not errors,
        errors=errors,
        notes=notes,
        duration_s=time.monotonic() - start,
    )


def final_validate(slug_dir: Path, skip_fact_validate: bool = False) -> StageResult:
    start = time.monotonic()
    data = _load(slug_dir)
    errors = validate(data, partial=False)
    notes: list[str] = []

    if not skip_fact_validate:
        # Best-effort Ollama fact validate. Non-blocking by design.
        try:
            import subprocess
            scripts_dir = Path(__file__).resolve().parents[1]
            vf = scripts_dir / "validate_facts.py"
            if vf.exists():
                subprocess.run(
                    ["python", str(vf), "--slug-dir", str(slug_dir)],
                    timeout=120, check=False,
                )
                notes.append("fact-validate ran (see unvalidated.md)")
        except Exception as e:
            notes.append(f"fact-validate skipped: {e}")

    return StageResult(passed=not errors, errors=errors, notes=notes, duration_s=time.monotonic() - start)
```

- [ ] **Step 4: Run tests, verify PASS**

```bash
pytest .claude/skills/itinerary-builder/scripts/tests/test_stage_runner.py -v
```

Expected: 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/itinerary-builder/scripts/lib/stage_runner.py .claude/skills/itinerary-builder/scripts/tests/test_stage_runner.py
git commit -m "feat(synth): add lib.stage_runner (per-stage validators + derivers)"
```

---

### Task 6: `scripts/synthesize.py` CLI

**Files:**
- Create: `.claude/skills/itinerary-builder/scripts/synthesize.py`
- Test: `.claude/skills/itinerary-builder/scripts/tests/test_synthesize_cli.py`

**Depends on:** Tasks 1–5.

- [ ] **Step 1: Write the failing tests**

Write `.claude/skills/itinerary-builder/scripts/tests/test_synthesize_cli.py`:

```python
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "synthesize.py"


def _run_cli(args, cwd):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, cwd=str(cwd),
    )


def test_cli_stage_1_passes_on_minimal(tmp_path, minimal_data):
    trips = tmp_path / "trips" / "test-slug"
    trips.mkdir(parents=True)
    (trips / "data.json").write_text(json.dumps(minimal_data), encoding="utf-8")
    res = _run_cli(["--slug", "test-slug", "--stage", "1", "--no-log"], cwd=tmp_path)
    assert res.returncode == 0, res.stdout + res.stderr


def test_cli_stage_1_fails_on_missing_required(tmp_path, minimal_data):
    trips = tmp_path / "trips" / "test-slug"
    trips.mkdir(parents=True)
    del minimal_data["metadata"]["pax"]
    (trips / "data.json").write_text(json.dumps(minimal_data), encoding="utf-8")
    res = _run_cli(["--slug", "test-slug", "--stage", "1", "--no-log"], cwd=tmp_path)
    assert res.returncode == 1
    assert "pax" in (res.stdout + res.stderr)


def test_cli_unknown_stage_errors(tmp_path, minimal_data):
    trips = tmp_path / "trips" / "test-slug"
    trips.mkdir(parents=True)
    (trips / "data.json").write_text(json.dumps(minimal_data), encoding="utf-8")
    res = _run_cli(["--slug", "test-slug", "--stage", "9", "--no-log"], cwd=tmp_path)
    assert res.returncode != 0


def test_cli_missing_data_json_errors(tmp_path):
    res = _run_cli(["--slug", "missing", "--stage", "1", "--no-log"], cwd=tmp_path)
    assert res.returncode != 0
    assert "data.json" in (res.stdout + res.stderr).lower()
```

- [ ] **Step 2: Run tests, verify FAIL**

```bash
pytest .claude/skills/itinerary-builder/scripts/tests/test_synthesize_cli.py -v
```

Expected: FAIL (file does not exist or returncode wrong).

- [ ] **Step 3: Implement `scripts/synthesize.py`**

Write `.claude/skills/itinerary-builder/scripts/synthesize.py`:

```python
"""Synthesizer CLI — orchestrates schema validation, geocoding, wiki precheck, and run logging.

Hard rule: this script never calls an LLM. All composition happens in-session via Claude.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from lib.stage_runner import run_stage, final_validate, StageResult
from lib.run_logger import RunLogger


def _trips_root() -> Path:
    env = os.environ.get("ITINERARY_TRIPS_ROOT")
    if env:
        return Path(env)
    return Path.cwd() / "trips"


def _runs_root() -> Path:
    return SCRIPTS_DIR.parent / "runs"


def _slug_dir(slug: str) -> Path:
    return _trips_root() / slug


def _print_result(stage_label: str, r: StageResult) -> None:
    status = "PASS" if r.passed else "FAIL"
    print(f"[{status}] stage {stage_label} ({r.duration_s:.2f}s)")
    for note in r.notes:
        print(f"  note: {note}")
    for err in r.errors:
        print(f"  error: {err}")


def cmd_stage(args) -> int:
    slug_dir = _slug_dir(args.slug)
    if not (slug_dir / "data.json").exists():
        print(f"error: {slug_dir / 'data.json'} not found", file=sys.stderr)
        return 1

    if args.no_log:
        r = run_stage(slug_dir, args.stage)
        _print_result(str(args.stage), r)
        return 0 if r.passed else 1

    inputs = {"slug": args.slug, "stage_first_invoked": args.stage}
    with RunLogger(slug=args.slug, runs_root=_runs_root(), inputs=inputs) as rl:
        rl.log_event(stage=args.stage, event="stage_start")
        r = run_stage(slug_dir, args.stage)
        rl.log_event(
            stage=args.stage,
            event="validate_pass" if r.passed else "validate_fail",
            details={"errors": r.errors, "notes": r.notes, "duration_s": r.duration_s},
        )
    _print_result(str(args.stage), r)
    return 0 if r.passed else 1


def cmd_final(args) -> int:
    slug_dir = _slug_dir(args.slug)
    if not (slug_dir / "data.json").exists():
        print(f"error: {slug_dir / 'data.json'} not found", file=sys.stderr)
        return 1

    if args.no_log:
        r = final_validate(slug_dir, skip_fact_validate=args.skip_facts)
        _print_result("final", r)
        return 0 if r.passed else 1

    with RunLogger(slug=args.slug, runs_root=_runs_root(),
                   inputs={"slug": args.slug, "stage_first_invoked": "final"}) as rl:
        rl.log_event(stage="final", event="stage_start")
        r = final_validate(slug_dir, skip_fact_validate=args.skip_facts)
        rl.log_event(
            stage="final",
            event="validate_pass" if r.passed else "validate_fail",
            details={"errors": r.errors, "notes": r.notes, "duration_s": r.duration_s},
        )
        if r.passed:
            rl.snapshot_data(slug_dir / "data.json")
    _print_result("final", r)
    return 0 if r.passed else 1


def cmd_learn(args) -> int:
    runs_root = _runs_root()
    if not runs_root.exists():
        print("no runs/ directory yet", file=sys.stderr)
        return 1
    cutoff_days = args.days
    import time
    cutoff = time.time() - cutoff_days * 86400
    feedback_files: list[Path] = []
    for run_dir in sorted(runs_root.iterdir()):
        fb = run_dir / "feedback.md"
        if fb.exists() and fb.stat().st_mtime >= cutoff:
            feedback_files.append(fb)
    if not feedback_files:
        print(f"no feedback files in the last {cutoff_days} days")
        return 0
    pending = runs_root / ".pending_learnings.md"
    with pending.open("w", encoding="utf-8") as out:
        for fb in feedback_files:
            out.write(f"## {fb.parent.name}\n\n")
            out.write(fb.read_text(encoding="utf-8"))
            out.write("\n\n---\n\n")
    print(f"Wrote {pending} ({len(feedback_files)} runs).")
    print("Next: open the file in chat and ask Claude to propose new learnings.md entries.")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Itinerary synthesizer (no-LLM CLI)")
    p.add_argument("--slug", required=False)
    p.add_argument("--stage", required=False, help="1-6, 'final', or 'learn'")
    p.add_argument("--no-log", action="store_true", help="Skip run logging (testing)")
    p.add_argument("--skip-facts", action="store_true", help="Skip Ollama fact-validate at final")
    p.add_argument("--days", type=int, default=30, help="For --stage learn: feedback age window")
    args = p.parse_args(argv)

    if args.stage == "learn":
        return cmd_learn(args)
    if args.stage == "final":
        if not args.slug:
            print("error: --slug required for --stage final", file=sys.stderr)
            return 2
        return cmd_final(args)

    try:
        args.stage = int(args.stage)
    except (TypeError, ValueError):
        print(f"error: --stage must be 1-6, 'final', or 'learn' (got {args.stage!r})", file=sys.stderr)
        return 2
    if not (1 <= args.stage <= 6):
        print(f"error: --stage must be 1-6 (got {args.stage})", file=sys.stderr)
        return 2
    if not args.slug:
        print("error: --slug required", file=sys.stderr)
        return 2
    return cmd_stage(args)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests, verify PASS**

```bash
pytest .claude/skills/itinerary-builder/scripts/tests/test_synthesize_cli.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Smoke against real fixture**

```bash
python .claude/skills/itinerary-builder/scripts/synthesize.py --slug manila --stage final --no-log --skip-facts
```

Expected: prints `[PASS] stage final ...`. If it fails, the manila fixture has gaps in the strict schema — investigate (don't fix the fixture, fix the validator if a rule is too strict).

- [ ] **Step 6: Commit**

```bash
git add .claude/skills/itinerary-builder/scripts/synthesize.py .claude/skills/itinerary-builder/scripts/tests/test_synthesize_cli.py
git commit -m "feat(synth): add synthesize.py CLI (stage/final/learn)"
```

---

## Wave 3 — Synth-prompt templates (Tasks 7-12 can run in parallel after Task 6)

Each template follows the same skeleton. Tasks 7-12 are otherwise independent.

### Common template skeleton

Each `references/synth_prompts/0N_<name>.md` follows this exact structure:

```markdown
# Stage N — <Name>

> **Read first:** `references/learnings.md` (curated lessons from prior runs)

## Inputs from prior stages
<bullet list of what should already be in data.json — empty for stage 1>

## What to produce in this stage
<3-6 sentences naming the schema blocks to fill>

## Schema fields to fill
<bulleted list of exact JSON paths from trip_data.schema.json that this stage owns>

## Quality bar
<bulleted heuristics for density, realism, sourcing>

## Reference snippets
<inline JSON snippets pulled from trips/manila/data.json and trips/da-nang/data.json>

## When done, run
```
python .claude/skills/itinerary-builder/scripts/synthesize.py --slug <slug> --stage N
```

If any errors: read them, patch data.json, re-run the same stage.
```

### Task 7: `synth_prompts/01_metadata_visa.md`

**Files:**
- Create: `.claude/skills/itinerary-builder/references/synth_prompts/01_metadata_visa.md`

- [ ] **Step 1: Create dir + write template**

```bash
mkdir -p .claude/skills/itinerary-builder/references/synth_prompts
```

Write the file with the skeleton above filled in. **Inputs:** none (stage 1 starts fresh). **What to produce:** `metadata{}` block (dates, origin, destination, passport, pax, base_hotel_area, currency_code, fx_rate_to_sgd, climate_summary, power_plug, weather_risk, tap_water, tipping, emergency) + `visa{}` block (rule, days_allowed, e_visa_required, passport_validity_required_until, onward_ticket_required, source).

**Quality bar:**
- Visa rule MUST be passport-specific. Cite source URL (gov / IATA Travel Centre).
- FX rate to SGD with anchor date (today's date by default).
- Climate summary uses destination + dates window (e.g. "Da Nang, mid-Aug → hot 32 °C, humidity 80%, typhoon-season-early, brief PM showers daily").
- `weather_risk`: low / medium / high (enum).

**Reference snippet** to embed in the file (literal JSON):

```json
{
  "metadata": {
    "dates_start": "2026-08-14",
    "dates_end": "2026-08-18",
    "origin": "Manila",
    "destination": "Da Nang",
    "passport": "PH",
    "pax": 2,
    "base_hotel_area": "My Khe Beach",
    "currency_code": "VND",
    "fx_rate_to_sgd": 18500,
    "fx_rate_anchor_date": "2026-05-29",
    "climate_summary": "Hot humid 32C, brief PM showers, early typhoon season",
    "power_plug": "Type A/C",
    "weather_risk": "medium",
    "tap_water": "Not potable — bottled only",
    "tipping": "5-10% appreciated",
    "emergency": "113 police, 115 ambulance"
  },
  "visa": {
    "rule": "Visa-exempt 21 days (PH-VN bilateral)",
    "days_allowed": 21,
    "e_visa_required": false,
    "passport_validity_required_until": "2027-02-14",
    "onward_ticket_required": true,
    "source": "https://vietnam.travel/visa"
  }
}
```

- [ ] **Step 2: Validate file is well-formed markdown**

```bash
test -f .claude/skills/itinerary-builder/references/synth_prompts/01_metadata_visa.md && echo OK
```

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/itinerary-builder/references/synth_prompts/01_metadata_visa.md
git commit -m "docs(synth): add stage-1 prompt template (metadata + visa)"
```

### Task 8: `synth_prompts/02_places.md`

**Files:**
- Create: `.claude/skills/itinerary-builder/references/synth_prompts/02_places.md`

**Parallelisable with Tasks 7, 9, 10, 11, 12.**

- [ ] **Step 1: Write the template**

Use the common skeleton.

**Inputs:** `metadata{}` and `visa{}` complete.

**What to produce:** `places[]` array of 15-25 entries covering categories `iconic`, `hidden_gem`, `food`, `spa`, `nightlife`, `hotel`, `indoor_backup`. Each entry MUST have at minimum: `key, name, category, area, description, distance_km_from_base, travel_min_from_base, price_label`. Add `wiki_title` for entries with Wikipedia coverage; add `alt_search_query` when no Wikipedia entry exists. Mark rain/heat refuges with `indoor: true`.

**Schema fields:** `places[].key`, `.name`, `.category`, `.area`, `.wiki_title`, `.alt_search_query`, `.description`, `.lat` (filled by stage runner), `.lon` (filled by stage runner), `.distance_km_from_base`, `.travel_min_from_base`, `.price_local`, `.price_label`, `.when`, `.indoor`, `.duration`, `.opening_hours`, `.links[]`.

**Quality bar:**
- ≥ 15 entries, ≤ 25 for a 5-day trip.
- Each category appears at least twice except `hotel` (covered by stage 3) and `indoor_backup` (≥ 3 for tropical / monsoon destinations).
- `description` ≥ 1 sentence, ≤ 3 sentences. Concrete details, no generic ad-copy.
- `wiki_title` uses underscores, no URL-encoding. Stage 2 runner will probe; misses are flagged for `alt_search_query`.
- `links[]` includes at least Google Maps + 1 review/official site.

**Reference snippet** (literal JSON, two entries):

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

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/itinerary-builder/references/synth_prompts/02_places.md
git commit -m "docs(synth): add stage-2 prompt template (places)"
```

### Task 9: `synth_prompts/03_hotels_pricing_budget.md`

**Files:**
- Create: `.claude/skills/itinerary-builder/references/synth_prompts/03_hotels_pricing_budget.md`

- [ ] **Step 1: Write the template**

**Inputs:** stages 1 + 2 complete.

**What to produce:** `hotels[]` (4-7 entries), `activity_pricing[]` (4-6 pick-ONE bundles), `budget{}` with categories + flight ranges.

**Schema fields:** `hotels[].{name, tier, rating, sgd_low, sgd_high, notes, links}`, `activity_pricing[].{category, paths[].{name, channel, local_per_pax, includes}}`, `budget.{rate_local_per_sgd, categories[].{category, low_local, high_local}, flight_sgd_low, flight_sgd_high, hotel_sgd_low, hotel_sgd_high}`.

**Quality bar:**
- Hotels cover tiers: ≥ 1 Budget, ≥ 1 Mid, ≥ 1 Luxury or Resort. SGD ranges realistic for destination + season.
- Activity pricing: each category has 2-3 paths (e.g. self-guided / DIY group / private tour). Channel names concrete ("Klook", "GetYourGuide", "hotel concierge", "grab car DIY").
- Budget categories at minimum: food, local transport, attractions, sims/wifi, misc.
- See `references/pricing_pattern.md` for the pick-ONE rule.

**Reference snippet** — three concise hotel entries, two pricing categories, six budget rows. (Pull literal JSON from `trips/manila/data.json` `hotels[0:3]` + `activity_pricing[0:2]` + `budget.categories[0:6]`.)

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/itinerary-builder/references/synth_prompts/03_hotels_pricing_budget.md
git commit -m "docs(synth): add stage-3 prompt template (hotels/pricing/budget)"
```

### Task 10: `synth_prompts/04_v1_itinerary.md`

**Files:**
- Create: `.claude/skills/itinerary-builder/references/synth_prompts/04_v1_itinerary.md`

- [ ] **Step 1: Write the template**

**Inputs:** stages 1-3 complete; `places[]` populated.

**What to produce:** `itinerary.v1_standard` — one entry per day, each with `day_label` + `rows[]`. Active hours ~13-14 per day.

**Schema fields:** `itinerary.v1_standard[].{day_label, rows[].{time, activity, route, km, min, cost_local, sgd, notes, place_key}}`.

**Quality bar:**
- Each row's `time` is `HH:MM` 24h. Stage 4 validator rejects malformed.
- Every row that references a place by name should also set `place_key` matching `places[].key`. Stage 4 rejects orphans.
- Each day has 6-12 rows: transit + visit + meal + buffer.
- `km` + `min` populated for every transit row.
- `cost_local` populated where there is a real cost; 0 for free entries; null for placeholder rows.
- See `references/variant_transforms.md` v1 rules.

**Reference snippet** (one day from `trips/da-nang/data.json` `v1_standard[0]`).

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/itinerary-builder/references/synth_prompts/04_v1_itinerary.md
git commit -m "docs(synth): add stage-4 prompt template (v1 itinerary)"
```

### Task 11: `synth_prompts/05_v2_v3_derive.md`

**Files:**
- Create: `.claude/skills/itinerary-builder/references/synth_prompts/05_v2_v3_derive.md`

- [ ] **Step 1: Write the template**

**Inputs:** stages 1-4 complete; v1 itinerary populated.

**What to produce:** `itinerary.v2_relaxed` (same shape as v1, derived from v1 via transforms from `references/variant_transforms.md`) + `itinerary.v3_weather` (per-day swap rows + indoor substitutes).

**Schema fields:** `itinerary.v2_relaxed[]`, `itinerary.v3_weather[]` (both same shape as v1).

**Quality bar:**
- v2 has same day count as v1 (stage 5 enforces).
- v2 swaps headline crowded sights for quieter alternatives from `places[]` with `category=hidden_gem` where available; caps active hours at 11-12.
- v3 has same day count as v1. Each day's rows should include rain-aware swaps drawing from `places[]` with `indoor=true`.
- Both v2 and v3 keep the SAME `day_label` strings as v1 to make the v1_v2_compare sheet line up.

**Reference snippet** — one v2 day + one v3 day pulled from `trips/da-nang/data.json`.

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/itinerary-builder/references/synth_prompts/05_v2_v3_derive.md
git commit -m "docs(synth): add stage-5 prompt template (v2/v3 derive)"
```

### Task 12: `synth_prompts/06_ancillary.md`

**Files:**
- Create: `.claude/skills/itinerary-builder/references/synth_prompts/06_ancillary.md`

- [ ] **Step 1: Write the template**

**Inputs:** stages 1-5 complete.

**What to produce:** all remaining blocks — `risk_flags[]`, `booking_timeline[]`, `practical_info[]`, `checklist[]`, `hidden_gems_categorized{}`, `v1_v2_compare[]`, `weather_plan_b{}` (decision_tree + per_day_swaps + booking_flex_tips — `indoor_bank` is auto-derived from `places[].indoor=true`), `maps{}` (regional + city_closeup configs with coords for ≥ 6 labelled places each), `transport_tips[]`, `accommodation_recommendation`, `practical_links{}`.

**Quality bar:**
- `booking_timeline[]` has 5-10 entries covering window from "12 weeks before" through "day-of".
- `practical_info[]` has 10-20 [label, text] pairs covering currency, payments, sim, transport, manners, safety.
- `checklist[]` has 15-30 entries grouped by category (Documents, Money, Health, Devices, Clothing, Day-Pack).
- `hidden_gems_categorized` has at least 3 categories.
- `weather_plan_b.decision_tree` has 5 levels (clear / PM showers / all-day rain / tropical storm / typhoon warning).
- `weather_plan_b.per_day_swaps` has one entry per day, each with 1-3 swaps.
- `maps.regional` zoom=10, `maps.city_closeup` zoom=12. Each `.places[]` entry has `lat, lon, label, color, pos`. Use coords already populated in `places[]` (stage 2 filled them).

**Reference snippet** — `booking_timeline[]` + `weather_plan_b{}` from `trips/manila/data.json` (literal JSON).

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/itinerary-builder/references/synth_prompts/06_ancillary.md
git commit -m "docs(synth): add stage-6 prompt template (ancillary blocks)"
```

---

## Wave 4 — Pipeline integration (Tasks 13, 14, 15, 16 are sequential, main agent)

### Task 13: Update `SKILL.md` Phase 1 Path B section

**Files:**
- Modify: `.claude/skills/itinerary-builder/SKILL.md`

- [ ] **Step 1: Read current Phase 1 wording**

Read lines around the "Path B" reference in SKILL.md (the long bullet that currently says "Compose from knowledge — Claude writes the data.json by hand").

- [ ] **Step 2: Replace Path B prose**

Replace the existing "Compose from knowledge" paragraph with:

```markdown
   - **Compose via staged synthesizer** — when no source doc, Claude uses the staged synth_prompts at `references/synth_prompts/0N_*.md`. Six stages: metadata+visa → places → hotels+pricing+budget → v1 itinerary → v2+v3 derive → ancillary. After each stage write data.json and run `python scripts/synthesize.py --slug <slug> --stage N` to validate. Validator output guides revisions. Final pass: `--stage final` runs strict schema + Ollama fact-validate (non-blocking). See [`references/workflow.md`](references/workflow.md) Phase 1 for the full flow and [`references/learnings.md`](references/learnings.md) for prior-run lessons that inform each stage.
```

- [ ] **Step 3: Update dependency list**

In the "## Dependencies" section, append `jsonschema`, `requests`, `pytest` to the `pip install` line:

```
pip install python-docx openpyxl Pillow staticmap jsonschema requests pytest
```

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/itinerary-builder/SKILL.md
git commit -m "docs(synth): rewrite SKILL.md Path B to staged synthesizer"
```

### Task 14: Update `references/workflow.md` Phase 1 + add Phase 10.5

**Files:**
- Modify: `.claude/skills/itinerary-builder/references/workflow.md`

- [ ] **Step 1: Replace Path B section in Phase 1**

Replace the entire "Path B — No source doc (compose from knowledge):" block (currently says "There is no automated synthesizer") with:

```markdown
**Path B — No source doc (staged synthesizer):**

Six sequential authoring stages. Each stage: read the corresponding `references/synth_prompts/0N_<name>.md` template + `references/learnings.md`, write the relevant blocks to `trips/<slug>/data.json`, then run:

```
python scripts/synthesize.py --slug <slug> --stage <N>
```

If the validator prints errors, patch `data.json` and re-run the same stage. Iterate until pass. Then move to stage N+1.

Stages:

1. **`01_metadata_visa.md`** — `metadata{}` + `visa{}` (passport-specific, sourced)
2. **`02_places.md`** — `places[]` 15-25 entries; runner auto-geocodes (Nominatim, cached) + probes Wikipedia for each `wiki_title`
3. **`03_hotels_pricing_budget.md`** — `hotels[]`, `activity_pricing[]`, `budget{}`
4. **`04_v1_itinerary.md`** — `itinerary.v1_standard` with full per-row time/km/min/cost
5. **`05_v2_v3_derive.md`** — `itinerary.v2_relaxed` + `itinerary.v3_weather` derived from v1
6. **`06_ancillary.md`** — `risk_flags`, `booking_timeline`, `practical_info`, `checklist`, `hidden_gems_categorized`, `v1_v2_compare`, `weather_plan_b`, `maps`, etc. Stage runner auto-derives `distance_matrix` + `weather_plan_b.indoor_bank`. Full strict schema enforced.

After stage 6:

```
python scripts/synthesize.py --slug <slug> --stage final
```

Runs strict schema check + invokes existing Ollama fact-validate (non-blocking; results in `trips/<slug>/unvalidated.md`). On pass, snapshots `data.json` to `runs/<run_id>/data.snapshot.json`.

Then proceed to Phase 6 (images / maps / workbook / docx) via `run_all.py`.

Expect 800-1500 lines for a 5-day trip across all stages combined. The staged structure prevents schema drift and keeps each phase resumable.
```

- [ ] **Step 2: Add Phase 10.5 — Feedback capture**

Insert a new section between Phase 10 (Delivery) and the end of the file:

```markdown
## Phase 10.5 — Feedback capture (NEW, optional)

After workbook + Word doc are delivered, prompt the user:

> "Trip rendered. Anything good/bad to capture for future runs?
>   - What worked well?
>   - What was thin or wrong?
>   - Specific places or sections that needed manual fix?"

Use `AskUserQuestion` with a single open-ended question. User may skip.

If a reply is given, write it verbatim to `runs/<run_id>/feedback.md`. The RunLogger will mark `feedback_captured: true` in `manifest.json`. Periodically run `python scripts/synthesize.py --stage learn` to surface candidate `references/learnings.md` entries from recent feedback; review in chat with Claude before appending.

The `learnings.md` file is read by every synth-prompt at every stage. That's the entire self-improvement loop.
```

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/itinerary-builder/references/workflow.md
git commit -m "docs(synth): rewrite workflow Phase 1 + add Phase 10.5 feedback capture"
```

### Task 15: Seed `references/learnings.md` + create `runs/.gitkeep`

**Files:**
- Create: `.claude/skills/itinerary-builder/references/learnings.md`
- Create: `.claude/skills/itinerary-builder/runs/.gitkeep`

- [ ] **Step 1: Write seed `learnings.md`**

```markdown
# Itinerary Synthesizer — Learnings

> Curated, append-only. Loaded by every stage of the staged synthesizer.
> Each entry should be one-line actionable. Tag with run_id when adding via `--stage learn`.

## Tropical SE-Asia
- (none yet — populated as runs complete)

## Non-tropical EU
- (none yet)

## Cold / Northern
- (none yet)

## Pricing
- (none yet)

## Place categories
- (none yet)

## Visa / passport gotchas
- (none yet)
```

- [ ] **Step 2: Create runs scaffold**

```bash
mkdir -p .claude/skills/itinerary-builder/runs
touch .claude/skills/itinerary-builder/runs/.gitkeep
```

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/itinerary-builder/references/learnings.md .claude/skills/itinerary-builder/runs/.gitkeep
git commit -m "docs(synth): seed learnings.md + runs/ scaffold"
```

### Task 16: Verify `--learn` end-to-end

**Files:** none new — exercises the CLI written in Task 6.

- [ ] **Step 1: Create a synthetic feedback file for the test**

```bash
mkdir -p .claude/skills/itinerary-builder/runs/2026-05-29T00-00-00_synthetic
echo "Day 2 had too few food spots. Skyline bar was closed." > .claude/skills/itinerary-builder/runs/2026-05-29T00-00-00_synthetic/feedback.md
echo "{\"run_id\": \"2026-05-29T00-00-00_synthetic\"}" > .claude/skills/itinerary-builder/runs/2026-05-29T00-00-00_synthetic/manifest.json
```

- [ ] **Step 2: Run `--stage learn`**

```bash
python .claude/skills/itinerary-builder/scripts/synthesize.py --stage learn --days 30
```

Expected: prints `Wrote .../runs/.pending_learnings.md (1 runs).` + the next-step hint.

- [ ] **Step 3: Verify pending file contents**

```bash
cat .claude/skills/itinerary-builder/runs/.pending_learnings.md
```

Expected: contains `## 2026-05-29T00-00-00_synthetic` header + the feedback text.

- [ ] **Step 4: Clean up synthetic test data + commit**

```bash
rm -rf .claude/skills/itinerary-builder/runs/2026-05-29T00-00-00_synthetic
rm -f .claude/skills/itinerary-builder/runs/.pending_learnings.md
git add -A .claude/skills/itinerary-builder/runs/
git commit -m "test(synth): verify --stage learn collates feedback (no-op commit if clean)" --allow-empty
```

---

## Wave 5 — Validation (Tasks 17, 18, 19 in parallel, Task 20 serial)

### Task 17: Integration test — synthesize.py final on Da Nang fixture

**Files:** none new — exercises existing fixture.

**Parallelisable with Tasks 18, 19.**

- [ ] **Step 1: Run final validation on da-nang**

```bash
python .claude/skills/itinerary-builder/scripts/synthesize.py --slug da-nang --stage final --no-log --skip-facts
```

Expected: `[PASS] stage final (...)`.

- [ ] **Step 2: If any errors, classify**

If errors print, decide:
- (a) Legacy fixture has fields not in schema → **fix the schema validation rule, not the fixture.** Add `additionalProperties: true` where appropriate or relax the field if it's clearly stale.
- (b) Real schema violation → **patch the fixture in-place** (case-by-case).

For each fix, write a one-line note to `docs/superpowers/specs/2026-05-29-itinerary-synthesizer-design.md` under a new section "## 14. Validation findings".

- [ ] **Step 3: Commit fixes if any**

```bash
git add -A
git commit -m "fix(synth): back-compat schema tweaks for legacy fixtures"
```

### Task 18: Integration test — synthesize.py final on Manila fixture

**Files:** none new.

**Parallelisable with Tasks 17, 19.**

- [ ] **Step 1: Run final on manila**

```bash
python .claude/skills/itinerary-builder/scripts/synthesize.py --slug manila --stage final --no-log --skip-facts
```

Expected: `[PASS] stage final (...)`.

- [ ] **Step 2: Same triage as Task 17 step 2 if errors print.**

- [ ] **Step 3: Commit any fixes.**

```bash
git add -A
git commit -m "fix(synth): back-compat schema for manila fixture"
```

### Task 19: Cross-climate cold-synthesis smoke (Lisbon)

**Files:**
- Create (via in-session Claude using stage 1-6 prompts): `trips/_test/lisbon/data.json`

**Parallelisable with Tasks 17, 18.**

- [ ] **Step 1: Bootstrap `trips/_test/lisbon/data.json`**

```bash
mkdir -p trips/_test/lisbon
echo '{"slug": "lisbon", "metadata": {}, "itinerary": {}, "places": []}' > trips/_test/lisbon/data.json
```

- [ ] **Step 2: Drive in-session synthesis stages 1-6**

In chat, Claude reads `references/synth_prompts/01_metadata_visa.md` through `06_ancillary.md` and authors `trips/_test/lisbon/data.json` for `Lisbon, Aug 14-18 2026, PH passport, 2 pax, base Bairro Alto`. After each stage, run:

```bash
ITINERARY_TRIPS_ROOT=$(pwd)/trips/_test python .claude/skills/itinerary-builder/scripts/synthesize.py --slug lisbon --stage <N> --no-log
```

Iterate until each stage passes.

- [ ] **Step 3: Final validation**

```bash
ITINERARY_TRIPS_ROOT=$(pwd)/trips/_test python .claude/skills/itinerary-builder/scripts/synthesize.py --slug lisbon --stage final --no-log --skip-facts
```

Expected: `[PASS] stage final`.

- [ ] **Step 4: Render workbook (sanity check, no docx required)**

```bash
ITINERARY_TRIPS_ROOT=$(pwd)/trips/_test python .claude/skills/itinerary-builder/scripts/build_workbook.py --slug lisbon
```

Expected: writes `trips/_test/lisbon/lisbon_Booking_Strategy.xlsx` without exception. Open + sanity-check 14 sheets.

- [ ] **Step 5: Commit (force-add since `trips/_test/` is gitignored)**

```bash
git add -f trips/_test/lisbon/data.json
git commit -m "test(synth): cross-climate Lisbon cold-synthesis fixture"
```

### Task 20: Full pytest suite + diff review

**Files:** none new.

**Depends on:** Tasks 1-19.

- [ ] **Step 1: Run full pytest**

```bash
cd C:/Dev/Active/itinerary-builder
pytest .claude/skills/itinerary-builder/scripts/tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 2: Dispatch `quality-reviewer` subagent**

Send a fresh subagent (subagent_type=quality-reviewer) with this prompt verbatim:

> Review the full diff on this branch — focus on `.claude/skills/itinerary-builder/scripts/lib/*.py`, `scripts/synthesize.py`, `scripts/tests/*.py`, and the new `references/synth_prompts/*.md`. Look for: (1) error handling that swallows real failures, (2) cache files written without dir creation, (3) any code path that calls an LLM at runtime (forbidden — synthesizer is in-session-Claude only), (4) tests that mock too aggressively to be useful, (5) inconsistent naming (e.g. `slug_dir` vs `slug`), (6) hidden mutable defaults. Return a punch list, severity-tagged. Under 400 words.

- [ ] **Step 3: Apply findings + commit**

```bash
git add -A
git commit -m "fix(synth): quality-reviewer punch list"
```

---

## Wave 6 — Second-opinion gate (Task 21, optional cut point)

### Task 21: Multi-model second-opinion review

**Files:** none new.

**Depends on:** Task 20.

- [ ] **Step 1: Dispatch `second-opinion` subagent**

Send a fresh subagent (subagent_type=second-opinion) with this prompt:

> Review the new files for the itinerary-synthesizer: `.claude/skills/itinerary-builder/scripts/lib/schema_check.py`, `geocode.py`, `wiki_precheck.py`, `stage_runner.py`, `run_logger.py`, `synthesize.py`. Also review the staged-prompt design in `references/synth_prompts/0N_*.md`. Cross-check against the spec at `docs/superpowers/specs/2026-05-29-itinerary-synthesizer-design.md`. Use 3 of: deepseek-pro, deepseek-flash, glm, minimax, gemma. Merge findings into a single punch list. Under 500 words.

- [ ] **Step 2: Triage findings — fix what matters, defer the rest**

For each finding:
- Severity HIGH/MEDIUM → fix inline + commit per fix
- LOW → file as follow-up task in plan (append to "Open follow-ups" section of the spec)

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "fix(synth): second-opinion punch list"
```

---

## Cut points if time-boxed

- **Skip Task 21** (Wave 6 second-opinion) — quality-reviewer in Task 20 already gives signal.
- **Skip Task 19** (Lisbon cross-climate) — defer until a real user requests a non-tropical destination.
- **Skip Task 16** (`--learn` smoke) — wire-up itself was tested in Task 6.

---

## Open follow-ups (post-v1)

These were noted in the spec; do NOT include in this plan:

- Free-form natural-language intake parsing
- Multi-pax mixed-passport handling
- Save-as-template (Bali → Tokyo derive)
- Auto-rebuild on schema migration
- CI hook (pre-push pytest + integration)

---

## Done criteria

- [ ] All 21 tasks complete, all commits clean
- [ ] `pytest .claude/skills/itinerary-builder/scripts/tests/` is all green
- [ ] `python synthesize.py --slug da-nang --stage final --no-log --skip-facts` returns 0
- [ ] `python synthesize.py --slug manila --stage final --no-log --skip-facts` returns 0
- [ ] Cross-climate cold synth (Lisbon) produces a valid data.json that renders a workbook
- [ ] `SKILL.md` Path B + `workflow.md` Phase 1 reflect the staged synthesizer
- [ ] `references/learnings.md` exists with empty seed sections
- [ ] `synthesize.py` never imports an LLM SDK (grep `grep -r "anthropic\|openai" scripts/`)
