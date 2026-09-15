import json
from unittest.mock import patch, MagicMock


from lib.geocode import Geocoder


def _mk_response(payload, status=200):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = payload
    r.raise_for_status.return_value = None
    return r


def test_geocode_hit_writes_cache(tmp_trip):
    cache = tmp_trip / ".cache" / "geocode.json"
    payload = [{"lat": "16.0544", "lon": "108.2022"}]
    with patch("lib.geocode.requests.get", return_value=_mk_response(payload)) as m:
        gc = Geocoder(cache_path=cache, sleep_s=0)
        lat, lon = gc.geocode("Dragon Bridge", "Da Nang", "Vietnam")
    assert (lat, lon) == (16.0544, 108.2022)
    assert m.call_count == 1
    stored = json.loads(cache.read_text(encoding="utf-8"))
    assert "Dragon Bridge|Da Nang|Vietnam" in stored


def test_geocode_uses_cache_on_second_call(tmp_trip):
    cache = tmp_trip / ".cache" / "geocode.json"
    cache.write_text(json.dumps({"X|A|C": [1.0, 2.0]}), encoding="utf-8")
    with patch("lib.geocode.requests.get") as m:
        gc = Geocoder(cache_path=cache, sleep_s=0)
        lat, lon = gc.geocode("X", "A", "C")
    assert (lat, lon) == (1.0, 2.0)
    assert m.call_count == 0


def test_geocode_miss_returns_none(tmp_trip):
    cache = tmp_trip / ".cache" / "geocode.json"
    with patch("lib.geocode.requests.get", return_value=_mk_response([])):
        gc = Geocoder(cache_path=cache, sleep_s=0)
        result = gc.geocode("Nowhere", "Nowhere", "Nowhere")
    assert result is None
    stored = json.loads(cache.read_text(encoding="utf-8"))
    assert stored["Nowhere|Nowhere|Nowhere"] is None


def test_geocode_429_retries_then_gives_up(tmp_trip):
    cache = tmp_trip / ".cache" / "geocode.json"
    resp_429 = _mk_response([], status=429)
    with patch("lib.geocode.requests.get", return_value=resp_429) as m, \
         patch("lib.geocode.time.sleep") as sleep_mock:
        gc = Geocoder(cache_path=cache, sleep_s=0, retry_backoff_s=0.01)
        result = gc.geocode("X", "Y", "Z")
    assert result is None
    assert m.call_count == 2  # initial + 1 retry
    assert sleep_mock.called


def test_geocode_batch_fills_in_place(tmp_trip):
    cache = tmp_trip / ".cache" / "geocode.json"
    payload = [{"lat": "10.0", "lon": "20.0"}]
    places = [
        {"key": "a", "name": "A", "area": "X"},  # no lat/lon
        {"key": "b", "name": "B", "area": "Y", "lat": 1.0, "lon": 2.0},  # already has
    ]
    with patch("lib.geocode.requests.get", return_value=_mk_response(payload)):
        gc = Geocoder(cache_path=cache, sleep_s=0)
        misses = gc.geocode_batch(places, country="Vietnam")
    assert places[0]["lat"] == 10.0 and places[0]["lon"] == 20.0
    assert places[1]["lat"] == 1.0  # unchanged
    assert misses == 0


def test_geocode_batch_counts_misses(tmp_trip):
    cache = tmp_trip / ".cache" / "geocode.json"
    with patch("lib.geocode.requests.get", return_value=_mk_response([])):
        gc = Geocoder(cache_path=cache, sleep_s=0)
        places = [{"key": "a", "name": "A", "area": "X"}]
        misses = gc.geocode_batch(places, country="Nowhere")
    assert misses == 1
    assert "lat" not in places[0]
