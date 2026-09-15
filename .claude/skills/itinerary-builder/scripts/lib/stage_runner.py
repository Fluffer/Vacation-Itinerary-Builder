"""Per-stage validators + auto-derivers + final-validate."""
from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from lib.schema_check import validate
from lib.geocode import Geocoder
from lib.wiki_precheck import WikiPrechecker

TIME_RE = re.compile(r"^([0-1]?\d|2[0-3]):[0-5]\d$|^[A-Za-z][A-Za-z0-9 \-/]{0,39}$")  # HH:MM or alpha-led label (e.g. "Sunrise", "All day", "Pre-dawn")


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
    # .get(): a malformed place must surface as a schema error later, not crash
    # the CLI with a KeyError before its own reporting runs.
    place_keys = {p.get("key") for p in data.get("places", []) if p.get("key")}
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
    # Auto-derive distance_matrix + indoor_bank using the shared helpers, so the
    # staged validator and the workbook renderer always produce identical rows.
    from lib.common import derive_distance_matrix, derive_indoor_bank

    data["distance_matrix"] = derive_distance_matrix(data)
    data.setdefault("weather_plan_b", {})["indoor_bank"] = derive_indoor_bank(data)

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
            import subprocess  # nosec B404
            scripts_dir = Path(__file__).resolve().parents[1]
            vf = scripts_dir / "validate_facts.py"
            if vf.exists():
                res = subprocess.run(  # nosec B603
                    [sys.executable, str(vf), "--slug-dir", str(slug_dir)],
                    timeout=120, check=False, capture_output=True, text=True, shell=False,
                )
                # Surface the outcome instead of always claiming it ran.
                if res.returncode == 0:
                    notes.append("fact-validate checklist written "
                                 "(see validate_prompts.md / unvalidated.md)")
                else:
                    notes.append(f"fact-validate failed (exit {res.returncode})")
        except Exception as e:
            notes.append(f"fact-validate skipped: {e}")

    return StageResult(passed=not errors, errors=errors, notes=notes, duration_s=time.monotonic() - start)
