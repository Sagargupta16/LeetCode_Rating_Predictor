"""Fixed-window per-IP rate limiting.

The API is public and unauthenticated, and every request costs a model
inference plus upstream LeetCode calls, so an unthrottled endpoint is an easy
way to burn the free-tier instance. This is deliberately in-process: it is a
brake against casual abuse, not a distributed quota system. Behind multiple
replicas each one keeps its own counter.
"""

from __future__ import annotations

import time
from collections import deque

from fastapi import HTTPException, Request


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        if max_requests <= 0:
            raise ValueError("max_requests must be positive")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self.max_requests = max_requests
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = {}

    def _prune(self, bucket: deque[float], now: float) -> None:
        cutoff = now - self.window
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()

    def check(self, key: str) -> None:
        """Record a hit for ``key``, raising 429 once the window is full."""
        now = time.monotonic()
        bucket = self._hits.setdefault(key, deque())
        self._prune(bucket, now)

        if len(bucket) >= self.max_requests:
            retry_after = max(1, int(self.window - (now - bucket[0])))
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please slow down.",
                headers={"Retry-After": str(retry_after)},
            )

        bucket.append(now)

    def cleanup(self) -> None:
        """Drop buckets that have fully expired, so memory does not creep."""
        now = time.monotonic()
        for key in list(self._hits):
            bucket = self._hits[key]
            self._prune(bucket, now)
            if not bucket:
                del self._hits[key]


def client_key(request: Request) -> str:
    """Identify the caller. Trusts the first X-Forwarded-For hop when present,
    since the app runs behind a proxy on Render."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
