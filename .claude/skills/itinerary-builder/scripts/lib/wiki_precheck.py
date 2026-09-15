"""Wikipedia REST page-summary probe with disk cache."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Iterable

import requests

WIKI_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/"
USER_AGENT = "itinerary-builder/1.0 (synthesizer)"


class WikiPrechecker:
    def __init__(
        self,
        cache_path: Path,
        sleep_s: float = 0.1,
        timeout_s: float = 5.0,
    ) -> None:
        self.cache_path = Path(cache_path)
        self.sleep_s = sleep_s
        self.timeout_s = timeout_s
        self._cache: dict[str, bool] = self._load_cache()

    def _load_cache(self) -> dict[str, bool]:
        if not self.cache_path.exists():
            return {}
        try:
            return json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_cache(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.cache_path.with_suffix(self.cache_path.suffix + ".tmp")
        tmp.write_text(json.dumps(self._cache, indent=2), encoding="utf-8")
        os.replace(tmp, self.cache_path)

    def precheck(self, title: str) -> bool:
        if title in self._cache:
            return self._cache[title]
        url = WIKI_URL + title
        headers = {"User-Agent": USER_AGENT}
        try:
            resp = requests.get(url, headers=headers, timeout=self.timeout_s)
        except requests.RequestException:
            # Transient — do not cache, so a later run retries.
            return False
        if resp.status_code == 200:
            self._cache[title] = True
            self._save_cache()
        elif resp.status_code == 404:
            # Definitive miss — safe to cache.
            self._cache[title] = False
            self._save_cache()
        else:
            # 429/5xx etc. are transient; return False without poisoning the cache.
            return False
        if self.sleep_s > 0:
            time.sleep(self.sleep_s)
        return self._cache[title]

    def precheck_places(self, places: Iterable[dict]) -> list[dict]:
        """For each place with `wiki_title`, probe and return result list.
        Entries without `wiki_title` get `hit=None`.
        """
        out = []
        for p in places:
            title = p.get("wiki_title")
            if not title:
                out.append({"key": p.get("key"), "wiki_title": None, "hit": None})
                continue
            out.append({"key": p.get("key"), "wiki_title": title, "hit": self.precheck(title)})
        return out
