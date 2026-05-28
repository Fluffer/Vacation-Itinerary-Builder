import json
from pathlib import Path

import pytest

from lib.schema_check import validate, validate_file


def test_partial_accepts_minimal(minimal_data):
    errors = validate(minimal_data, partial=True)
    assert errors == []


def test_strict_passes_for_complete_minimal_shape(minimal_data):
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
