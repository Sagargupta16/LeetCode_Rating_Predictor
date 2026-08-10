import asyncio

import httpx
import pytest
from fastapi import HTTPException

from app.services.leetcode import fetch_attended_contests
from app.utils.cache import TTLCache


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeClient:
    def __init__(self, payload):
        self._payload = payload

    async def post(self, *args, **kwargs):
        return FakeResponse(self._payload)


def _history(*entries):
    return {"data": {"userContestRankingHistory": list(entries)}}


def _entry(slug, rank, attended=True, rating=1800.0):
    return {
        "attended": attended,
        "ranking": rank,
        "rating": rating,
        "contest": {"title": slug.replace("-", " ").title(), "titleSlug": slug},
    }


def _run(payload, **kwargs):
    return asyncio.run(
        fetch_attended_contests(
            FakeClient(payload), asyncio.Semaphore(5), TTLCache(), "someuser", **kwargs
        )
    )


def test_returns_attended_contests_newest_first():
    result = _run(
        _history(
            _entry("weekly-contest-370", 900),
            _entry("weekly-contest-371", 800),
        )
    )
    assert [c["name"] for c in result] == [
        "weekly-contest-371",
        "weekly-contest-370",
    ]
    assert result[0]["rank"] == 800


def test_skips_unattended_contests():
    result = _run(
        _history(
            _entry("weekly-contest-370", 900),
            _entry("weekly-contest-371", 0, attended=False),
        )
    )
    assert [c["name"] for c in result] == ["weekly-contest-370"]


def test_skips_contests_with_unsupported_slugs():
    """Slugs must round-trip into /api/predict, which validates the pattern."""
    result = _run(
        _history(
            _entry("spring-challenge-2024", 10),
            _entry("biweekly-contest-120", 55),
        )
    )
    assert [c["name"] for c in result] == ["biweekly-contest-120"]


def test_skips_invalid_rankings():
    result = _run(
        _history(
            _entry("weekly-contest-370", 0),
            _entry("weekly-contest-371", -5),
            _entry("weekly-contest-372", 12),
        )
    )
    assert [c["name"] for c in result] == ["weekly-contest-372"]


def test_respects_limit():
    entries = [_entry(f"weekly-contest-{370 + i}", 100 + i) for i in range(8)]
    result = _run(_history(*entries), limit=3)
    assert len(result) == 3
    assert result[0]["name"] == "weekly-contest-377"


def test_missing_history_is_a_client_error():
    coro = fetch_attended_contests(
        FakeClient({"data": {"userContestRankingHistory": None}}),
        asyncio.Semaphore(5),
        TTLCache(),
        "ghost",
    )
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(coro)
    assert exc_info.value.status_code == 400


def test_upstream_failure_maps_to_503():
    class BrokenClient:
        async def post(self, *args, **kwargs):
            raise httpx.HTTPError("boom")

    coro = fetch_attended_contests(
        BrokenClient(), asyncio.Semaphore(5), TTLCache(), "someuser"
    )
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(coro)
    assert exc_info.value.status_code == 503


def test_results_are_cached():
    cache = TTLCache()
    payload = _history(_entry("weekly-contest-370", 900))
    client = FakeClient(payload)

    first = asyncio.run(
        fetch_attended_contests(client, asyncio.Semaphore(5), cache, "someuser")
    )

    class ExplodingClient:
        async def post(self, *args, **kwargs):
            raise AssertionError("should have been served from cache")

    second = asyncio.run(
        fetch_attended_contests(
            ExplodingClient(), asyncio.Semaphore(5), cache, "someuser"
        )
    )
    assert first == second
