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


def test_exit_records_outcome_ok(tmp_path):
    runs_root = tmp_path / "runs"
    with RunLogger(slug="x", runs_root=runs_root, inputs={}) as rl:
        pass
    manifest = json.loads((rl.run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["outcome"] == "ok"


def test_exit_records_outcome_exception(tmp_path):
    runs_root = tmp_path / "runs"
    try:
        with RunLogger(slug="x", runs_root=runs_root, inputs={}) as rl:
            run_dir = rl.run_dir
            raise ValueError("test")
    except ValueError:
        pass
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["outcome"] == "exception"
    assert manifest["exception_type"] == "ValueError"
