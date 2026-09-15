"""Regression tests for the code-review fixes."""
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from lib.common import derive_distance_matrix, derive_indoor_bank
from lib.geocode import Geocoder
from lib.wiki_precheck import WikiPrechecker
from lib.stage_runner import final_validate


def _write_data(slug_dir: Path, data: dict) -> None:
    (slug_dir / "data.json").write_text(json.dumps(data), encoding="utf-8")


def _mk_response(payload=b"{}", status=200, ctype="application/json"):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = payload
    r.headers = {"Content-Type": ctype}
    r.read.return_value = payload if isinstance(payload, bytes) else b""
    r.raise_for_status.return_value = None
    return r


# --- geocode: transient failures are not cached ------------------------------

def test_geocode_does_not_cache_transient_exception(tmp_trip):
    cache = tmp_trip / ".cache" / "geocode.json"
    with patch("lib.geocode.requests.get", side_effect=requests.RequestException("boom")):
        assert Geocoder(cache_path=cache, sleep_s=0).geocode("X", "Y", "Z") is None
    stored = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else {}
    assert "X|Y|Z" not in stored  # must retry on a later run


def test_geocode_429_is_not_cached(tmp_trip):
    cache = tmp_trip / ".cache" / "geocode.json"
    with patch("lib.geocode.requests.get", return_value=_mk_response([], status=429)), \
         patch("lib.geocode.time.sleep"):
        assert Geocoder(cache_path=cache, sleep_s=0, retry_backoff_s=0).geocode("X", "Y", "Z") is None
    stored = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else {}
    assert "X|Y|Z" not in stored


def test_geocode_empty_result_is_cached(tmp_trip):
    cache = tmp_trip / ".cache" / "geocode.json"
    with patch("lib.geocode.requests.get", return_value=_mk_response([])):
        assert Geocoder(cache_path=cache, sleep_s=0).geocode("Nowhere", "A", "B") is None
    assert json.loads(cache.read_text(encoding="utf-8"))["Nowhere|A|B"] is None


# --- wiki_precheck: only 404 is cached ---------------------------------------

def test_wiki_precheck_transient_not_cached(tmp_trip):
    cache = tmp_trip / ".cache" / "wiki.json"
    with patch("lib.wiki_precheck.requests.get", side_effect=requests.RequestException("x")):
        assert WikiPrechecker(cache_path=cache, sleep_s=0).precheck("Foo") is False
    assert "Foo" not in (json.loads(cache.read_text()) if cache.exists() else {})


def test_wiki_precheck_5xx_not_cached(tmp_trip):
    cache = tmp_trip / ".cache" / "wiki.json"
    with patch("lib.wiki_precheck.requests.get", return_value=_mk_response(status=503)):
        assert WikiPrechecker(cache_path=cache, sleep_s=0).precheck("Foo") is False
    assert "Foo" not in (json.loads(cache.read_text()) if cache.exists() else {})


def test_wiki_precheck_404_is_cached(tmp_trip):
    cache = tmp_trip / ".cache" / "wiki.json"
    with patch("lib.wiki_precheck.requests.get", return_value=_mk_response(status=404)):
        assert WikiPrechecker(cache_path=cache, sleep_s=0).precheck("Foo") is False
    assert json.loads(cache.read_text())["Foo"] is False


# --- shared derivation: exact de-dup -----------------------------------------

def test_derive_distance_matrix_does_not_substring_collide():
    data = {
        "metadata": {"base_hotel_area": "Base"},
        "distance_matrix": [{"from": "Base", "to": "My Khe Beach", "km": 1, "min": 2}],
        "places": [
            {"name": "Beach", "distance_km_from_base": 3, "travel_min_from_base": 4},
            {"name": "My Khe Beach", "distance_km_from_base": 1, "travel_min_from_base": 2},
        ],
    }
    tos = [r["to"] for r in derive_distance_matrix(data)]
    assert "Beach" in tos                 # not suppressed by "My Khe Beach"
    assert tos.count("My Khe Beach") == 1  # exact duplicate not re-added


def test_derive_distance_matrix_tolerates_empty_to():
    data = {
        "distance_matrix": [{"from": "B", "to": "", "km": 0, "min": 0}],
        "places": [{"name": "X", "distance_km_from_base": 1, "travel_min_from_base": 2}],
    }
    assert any(r["to"] == "X" for r in derive_distance_matrix(data))


def test_derive_indoor_bank_exact_dedup():
    data = {
        "weather_plan_b": {"indoor_bank": [{"name": "Museum"}]},
        "places": [{"name": "Museum", "indoor": True}, {"name": "Aquarium", "indoor": True}],
    }
    names = [b["name"] for b in derive_indoor_bank(data)]
    assert names.count("Museum") == 1
    assert "Aquarium" in names


# --- fetch_images: non-image responses rejected ------------------------------

def test_fetch_rejects_non_image(tmp_path):
    import fetch_images

    resp = _mk_response(b"<svg></svg>", status=200, ctype="image/svg+xml")
    resp.__enter__ = lambda s: s
    resp.__exit__ = lambda *a: False
    with patch("urllib.request.urlopen", return_value=resp):
        assert fetch_images.fetch("https://x/y.svg", str(tmp_path / "y.jpg")) is None
    assert not (tmp_path / "y.jpg").exists()


def test_fetch_rejects_non_https_scheme(tmp_path):
    import fetch_images

    assert fetch_images.fetch("file:///etc/passwd", str(tmp_path / "z.jpg")) is None
    assert not (tmp_path / "z.jpg").exists()


# --- final_validate: surfaces the fact-validate outcome ----------------------

def test_final_validate_surfaces_failure_and_passes_accepted_args(tmp_trip, minimal_data):
    minimal_data["itinerary"] = {
        "v1_standard": [{"day_label": "D1", "rows": []}],
        "v2_relaxed": [{"day_label": "D1", "rows": []}],
        "v3_weather": [{"day_label": "D1", "rows": []}],
    }
    _write_data(tmp_trip, minimal_data)
    m = MagicMock()
    m.returncode = 2
    with patch("subprocess.run", return_value=m) as run_mock:
        result = final_validate(slug_dir=tmp_trip, skip_fact_validate=False)
    assert any("failed" in n for n in result.notes)
    called = run_mock.call_args[0][0]
    assert "--slug-dir" in called or "--slug" in called


# --- run_all: timeout is handled ---------------------------------------------

def test_run_all_timeout_on_required_step_raises():
    from run_all import PipelineError, run

    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("x", 1)):
        with pytest.raises(PipelineError):
            run("fetch_images.py", "slug")


def test_run_all_timeout_on_optional_step_continues():
    from run_all import run

    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("x", 1)):
        run("fetch_images.py", "slug", required=False)  # must not raise


# --- validate_facts CLI: --slug-dir + unvalidated.md -------------------------

def test_build_workbook_emits_v3_and_calcs(tmp_path, minimal_data, monkeypatch):
    import copy

    import build_workbook
    from openpyxl import load_workbook

    data = copy.deepcopy(minimal_data)
    data["places"] = [{"key": "p1", "name": "P1", "category": "iconic", "indoor": True}]
    data["itinerary"] = {
        "v1_standard": [{"day_label": "Day 1", "rows": []}],
        "v2_relaxed": [{"day_label": "Day 1", "rows": []}],
        "v3_weather": [{"day_label": "Day 1", "rows": []}],
    }
    # Content but NO explicit emit flag → the Plan B sheet must still be emitted.
    data["weather_plan_b"] = {
        "decision_tree": [{"condition": "clear", "trigger": "dry", "action": "go"}],
    }
    # An explicit null extras array must not raise TypeError.
    data["activity_pricing"] = [
        {"category": "Tours", "paths": [{"name": "Klook", "channel": "Klook"}], "extras": None}
    ]
    out = tmp_path / "wb.xlsx"
    monkeypatch.setattr(build_workbook, "load_data", lambda s: data)
    monkeypatch.setattr(build_workbook, "out_xlsx", lambda s: str(out))

    build_workbook.build("slug")

    wb = load_workbook(out)
    assert "5. v3 Weather Itinerary" in wb.sheetnames
    assert "5. v3 Bad Weather Plan B" in wb.sheetnames
    assert wb.calculation.fullCalcOnLoad is True


def test_validate_facts_cli_writes_outputs(tmp_path, minimal_data):
    # Directory deliberately OUTSIDE any ITINERARY_TRIPS_ROOT: --slug-dir must be
    # honored verbatim (not re-resolved by basename under the trips root).
    slug_dir = tmp_path / "elsewhere" / "test-slug"
    slug_dir.mkdir(parents=True)
    _write_data(slug_dir, minimal_data)
    script = Path(__file__).resolve().parent.parent / "validate_facts.py"
    env = {**__import__("os").environ, "ITINERARY_TRIPS_ROOT": str(tmp_path / "unused")}
    r = subprocess.run([sys.executable, str(script), "--slug-dir", str(slug_dir)],
                       env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert (slug_dir / "validate_prompts.md").exists()
    assert (slug_dir / "unvalidated.md").exists()
