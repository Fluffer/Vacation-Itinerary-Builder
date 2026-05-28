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
