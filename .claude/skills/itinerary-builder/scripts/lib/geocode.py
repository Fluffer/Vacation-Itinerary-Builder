"""Nominatim geocoder with per-trip disk cache + rate-limit handling."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Iterable

import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "itinerary-builder/1.0 (synthesizer)"


class Geocoder:
    def __init__(
        self,
        cache_path: Path,
        sleep_s: float = 1.1,
        timeout_s: float = 5.0,
        retry_backoff_s: float = 30.0,
    ) -> None:
        self.cache_path = Path(cache_path)
        self.sleep_s = sleep_s
        self.timeout_s = timeout_s
        self.retry_backoff_s = retry_backoff_s
        self._cache: dict[str, tuple[float, float] | None] = self._load_cache()

    def _load_cache(self) -> dict:
        if not self.cache_path.exists():
            return {}
        try:
            raw = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
        return {k: (tuple(v) if isinstance(v, list) else None) for k, v in raw.items()}

    def _save_cache(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        serialisable = {k: (list(v) if v is not None else None) for k, v in self._cache.items()}
        tmp = self.cache_path.with_suffix(self.cache_path.suffix + ".tmp")
        tmp.write_text(json.dumps(serialisable, indent=2), encoding="utf-8")
        os.replace(tmp, self.cache_path)

    @staticmethod
    def _key(name: str, area: str, country: str) -> str:
        return f"{name}|{area}|{country}"

    def geocode(self, name: str, area: str, country: str) -> tuple[float, float] | None:
        key = self._key(name, area, country)
        if key in self._cache:
            return self._cache[key]

        query = ", ".join(p for p in (name, area, country) if p)
        params = {"q": query, "format": "json", "limit": 1}
        headers = {"User-Agent": USER_AGENT}

        for attempt in (0, 1):  # initial + 1 retry on 429
            try:
                resp = requests.get(
                    NOMINATIM_URL, params=params, headers=headers, timeout=self.timeout_s
                )
            except requests.RequestException:
                # Transient failure — do NOT cache, so a later run retries.
                return None

            if resp.status_code == 429 and attempt == 0:
                time.sleep(self.retry_backoff_s)
                continue
            if resp.status_code != 200:
                # 429/5xx are transient; only a definitive miss is cached below.
                return None

            data = resp.json()
            if not data:
                # Definitive: Nominatim found nothing for this query — cache it.
                self._cache[key] = None
                self._save_cache()
                return None

            lat = float(data[0]["lat"])
            lon = float(data[0]["lon"])
            self._cache[key] = (lat, lon)
            self._save_cache()
            if self.sleep_s > 0:
                time.sleep(self.sleep_s)
            return (lat, lon)

        # all attempts exhausted on 429 — transient, do not cache
        return None

    def geocode_batch(self, places: Iterable[dict], country: str) -> int:
        """Fill lat/lon in-place for any place missing them. Returns miss count."""
        misses = 0
        for p in places:
            if p.get("lat") is not None and p.get("lon") is not None:
                continue
            result = self.geocode(p.get("name", ""), p.get("area", ""), country)
            if result is None:
                misses += 1
            else:
                p["lat"], p["lon"] = result
        return misses
