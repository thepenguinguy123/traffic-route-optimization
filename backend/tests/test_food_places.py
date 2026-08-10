"""Unit tests for the resilient Goong Places collector."""

from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

from backend.app.services.food_places import (
    DEFAULT_SEARCH_TERMS,
    load_search_terms,
    request_json,
)


class _FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return b'{"status":"OK","predictions":[]}'


def test_request_json_retries_transient_network_errors():
    failures = [URLError("connection reset"), URLError("timeout")]

    def fake_urlopen(request, timeout):
        if failures:
            raise failures.pop(0)
        return _FakeResponse()

    with patch(
        "backend.app.services.food_places.urlopen",
        side_effect=fake_urlopen,
    ) as mocked_urlopen, patch(
        "backend.app.services.food_places.time.sleep",
    ) as mocked_sleep:
        payload = request_json("https://example.test", {"q": "food"})

    assert payload["status"] == "OK"
    assert mocked_urlopen.call_count == 3
    assert mocked_sleep.call_count == 2


def test_load_search_terms_preserves_order_and_removes_duplicates(tmp_path: Path):
    terms_path = tmp_path / "terms.json"
    terms_path.write_text(
        '["coffee", "c\u00e0 ph\u00ea", "coffee", "  tea  ", ""]',
        encoding="utf-8",
    )

    assert load_search_terms(terms_path) == ("coffee", "c\u00e0 ph\u00ea", "tea")


def test_load_search_terms_uses_safe_defaults_for_invalid_data(tmp_path: Path):
    terms_path = tmp_path / "terms.json"
    terms_path.write_text('{"term": "coffee"}', encoding="utf-8")

    assert load_search_terms(terms_path) == DEFAULT_SEARCH_TERMS
