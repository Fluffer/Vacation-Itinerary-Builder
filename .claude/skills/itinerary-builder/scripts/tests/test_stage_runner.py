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


def test_stage_4_rejects_garbage_time(tmp_trip, minimal_data):
    minimal_data["itinerary"] = {
        "v1_standard": [{
            "day_label": "Day 1",
            "rows": [{"time": "12345", "activity": "garbage"}],
        }],
    }
    _write_data(tmp_trip, minimal_data)
    result = run_stage(slug_dir=tmp_trip, stage_num=4)
    assert result.passed is False
    assert any("bad time format" in e for e in result.errors)


def test_stage_4_accepts_alpha_label(tmp_trip, minimal_data):
    minimal_data["itinerary"] = {
        "v1_standard": [{
            "day_label": "Day 1",
            "rows": [{"time": "Sunrise", "activity": "watch sunrise"}],
        }],
    }
    _write_data(tmp_trip, minimal_data)
    result = run_stage(slug_dir=tmp_trip, stage_num=4)
    # No "bad time format" error for the row (other partial-schema errors are tolerable here)
    assert not any("bad time format" in e for e in result.errors)


def test_stage_6_rejects_booking_flex_tips_strings(tmp_trip, minimal_data):
    minimal_data["itinerary"] = {
        "v1_standard": [{"day_label": "Day 1", "rows": []}],
        "v2_relaxed": [{"day_label": "Day 1", "rows": []}],
        "v3_weather": [{"day_label": "Day 1", "rows": []}],
    }
    minimal_data["weather_plan_b"] = {
        "emit": True,
        "indoor_bank": [],
        "booking_flex_tips": ["plain string not allowed"],
    }
    _write_data(tmp_trip, minimal_data)
    result = run_stage(slug_dir=tmp_trip, stage_num=6)
    assert result.passed is False
    assert any("booking_flex_tips" in e for e in result.errors)
