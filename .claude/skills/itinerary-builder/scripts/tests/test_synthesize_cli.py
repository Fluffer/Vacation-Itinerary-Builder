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
    assert res.returncode == 2


def test_cli_missing_data_json_errors(tmp_path):
    res = _run_cli(["--slug", "missing", "--stage", "1", "--no-log"], cwd=tmp_path)
    assert res.returncode != 0
    assert "data.json" in (res.stdout + res.stderr).lower()
