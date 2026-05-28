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
