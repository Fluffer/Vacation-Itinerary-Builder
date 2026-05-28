import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from lib.wiki_precheck import WikiPrechecker


def _mk(status: int):
    r = MagicMock()
    r.status_code = status
    return r


def test_hit_returns_true(tmp_trip):
    cache = tmp_trip / ".cache" / "wiki.json"
    with patch("lib.wiki_precheck.requests.get", return_value=_mk(200)):
        pc = WikiPrechecker(cache_path=cache, sleep_s=0)
        assert pc.precheck("Dragon_Bridge") is True
    stored = json.loads(cache.read_text(encoding="utf-8"))
    assert stored["Dragon_Bridge"] is True


def test_miss_returns_false(tmp_trip):
    cache = tmp_trip / ".cache" / "wiki.json"
    with patch("lib.wiki_precheck.requests.get", return_value=_mk(404)):
        pc = WikiPrechecker(cache_path=cache, sleep_s=0)
        assert pc.precheck("Nope_Place") is False
    stored = json.loads(cache.read_text(encoding="utf-8"))
    assert stored["Nope_Place"] is False


def test_uses_cache(tmp_trip):
    cache = tmp_trip / ".cache" / "wiki.json"
    cache.write_text(json.dumps({"X": True}), encoding="utf-8")
    with patch("lib.wiki_precheck.requests.get") as m:
        pc = WikiPrechecker(cache_path=cache, sleep_s=0)
        assert pc.precheck("X") is True
    assert m.call_count == 0


def test_precheck_places_returns_per_entry(tmp_trip):
    cache = tmp_trip / ".cache" / "wiki.json"
    def side_effect(url, **kw):
        return _mk(200 if "Bridge" in url else 404)
    with patch("lib.wiki_precheck.requests.get", side_effect=side_effect):
        pc = WikiPrechecker(cache_path=cache, sleep_s=0)
        results = pc.precheck_places([
            {"key": "a", "wiki_title": "Dragon_Bridge"},
            {"key": "b", "wiki_title": "Nope"},
            {"key": "c"},  # no wiki_title — skipped
        ])
    keys = {r["key"]: r["hit"] for r in results}
    assert keys == {"a": True, "b": False, "c": None}
