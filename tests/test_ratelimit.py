import pytest
from fastapi import HTTPException

from app.utils.ratelimit import RateLimiter


def test_allows_requests_under_the_limit():
    limiter = RateLimiter(max_requests=3, window_seconds=60)
    for _ in range(3):
        limiter.check("1.2.3.4")


def test_blocks_once_the_window_is_full():
    limiter = RateLimiter(max_requests=2, window_seconds=60)
    limiter.check("1.2.3.4")
    limiter.check("1.2.3.4")
    with pytest.raises(HTTPException) as exc_info:
        limiter.check("1.2.3.4")
    assert exc_info.value.status_code == 429
    assert "Retry-After" in exc_info.value.headers


def test_buckets_are_per_client():
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    limiter.check("1.1.1.1")
    limiter.check("2.2.2.2")
    with pytest.raises(HTTPException):
        limiter.check("1.1.1.1")


def test_window_expiry_frees_capacity(monkeypatch):
    limiter = RateLimiter(max_requests=1, window_seconds=10)
    clock = {"now": 1000.0}
    monkeypatch.setattr("app.utils.ratelimit.time.monotonic", lambda: clock["now"])

    limiter.check("1.2.3.4")
    with pytest.raises(HTTPException):
        limiter.check("1.2.3.4")

    clock["now"] += 11
    limiter.check("1.2.3.4")


def test_cleanup_drops_expired_buckets(monkeypatch):
    limiter = RateLimiter(max_requests=5, window_seconds=10)
    clock = {"now": 500.0}
    monkeypatch.setattr("app.utils.ratelimit.time.monotonic", lambda: clock["now"])

    limiter.check("1.2.3.4")
    assert limiter._hits

    clock["now"] += 11
    limiter.cleanup()
    assert not limiter._hits


@pytest.mark.parametrize("bad_args", [(0, 60), (5, 0), (-1, 60)])
def test_rejects_invalid_configuration(bad_args):
    with pytest.raises(ValueError):
        RateLimiter(*bad_args)
