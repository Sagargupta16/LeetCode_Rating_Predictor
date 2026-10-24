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

from app.config import CLIENT_IP_HEADER


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        if max_requests <= 0:
            raise ValueError("max_requests must be positive")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self.max_requests = max_requests
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = {}
        self._next_sweep = 0.0

    def _prune(self, bucket: deque[float], now: float) -> None:
        cutoff = now - self.window
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()

    def check(self, key: str) -> None:
        """Record a hit for ``key``, raising 429 once the window is full."""
        now = time.monotonic()
        # Every client that ever called leaves a bucket behind, so sweep the
        # expired ones once per window instead of letting the dict grow.
        if now >= self._next_sweep:
            self.cleanup()
            self._next_sweep = now + self.window
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
        for bucket in self._hits.values():
            self._prune(bucket, now)
        expired = [key for key, bucket in self._hits.items() if not bucket]
        for key in expired:
            del self._hits[key]


def client_key(request: Request) -> str:
    """Identify the caller.

    Uses ``CLIENT_IP_HEADER`` when one is configured and present, since only a
    proxy that overwrites the header makes it trustworthy (Cloudflare sets
    CF-Connecting-IP in front of Render). Otherwise the socket peer.
    X-Forwarded-For is never read: its first entry is client-supplied, so
    keying on it let anyone skip the limit by sending a new value each time.
    """
    if CLIENT_IP_HEADER:
        forwarded = request.headers.get(CLIENT_IP_HEADER, "").strip()
        if forwarded:
            return forwarded
    return request.client.host if request.client else "unknown"
