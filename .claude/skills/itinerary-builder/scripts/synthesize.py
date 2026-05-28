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


def _pointer_path() -> Path:
    return _runs_root() / ".current_run"


def _read_pointer(slug: str) -> str | None:
    p = _pointer_path()
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if data.get("slug") != slug:
        return None
    return data.get("run_id")


def _write_pointer(slug: str, run_id: str) -> None:
    p = _pointer_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"slug": slug, "run_id": run_id}), encoding="utf-8")


def _clear_pointer() -> None:
    p = _pointer_path()
    if p.exists():
        p.unlink()


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

    existing_run_id = _read_pointer(args.slug)
    inputs = {"slug": args.slug, "stage_first_invoked": args.stage}
    if existing_run_id:
        rl_cm = RunLogger.resume(slug=args.slug, run_id=existing_run_id, runs_root=_runs_root())
    else:
        rl_cm = RunLogger(slug=args.slug, runs_root=_runs_root(), inputs=inputs)
    with rl_cm as rl:
        if not existing_run_id:
            _write_pointer(args.slug, rl.run_id)
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

    existing_run_id = _read_pointer(args.slug)
    if existing_run_id:
        rl_cm = RunLogger.resume(slug=args.slug, run_id=existing_run_id, runs_root=_runs_root())
    else:
        rl_cm = RunLogger(slug=args.slug, runs_root=_runs_root(),
                          inputs={"slug": args.slug, "stage_first_invoked": "final"})
    with rl_cm as rl:
        if not existing_run_id:
            _write_pointer(args.slug, rl.run_id)
        rl.log_event(stage="final", event="stage_start")
        r = final_validate(slug_dir, skip_fact_validate=args.skip_facts)
        rl.log_event(
            stage="final",
            event="validate_pass" if r.passed else "validate_fail",
            details={"errors": r.errors, "notes": r.notes, "duration_s": r.duration_s},
        )
        if r.passed:
            rl.snapshot_data(slug_dir / "data.json")
            _clear_pointer()
    _print_result("final", r)
    return 0 if r.passed else 1


def cmd_learn(args) -> int:
    runs_root = _runs_root()
    if not runs_root.exists():
        print("no runs/ directory yet")
        return 0
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
