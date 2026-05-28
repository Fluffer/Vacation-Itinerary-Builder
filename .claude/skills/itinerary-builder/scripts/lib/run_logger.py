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
