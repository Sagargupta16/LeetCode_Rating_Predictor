"""In-memory TTL cache and optional Redis cache."""

import json
import os
import time
from typing import Any, Optional

try:
    import redis
except Exception:
    redis = None


class TTLCache:
    def __init__(self, ttl_seconds: int = 300):
        if ttl_seconds <= 0:
            raise ValueError("TTL must be a positive integer")
        self.ttl = ttl_seconds
        self._store: dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expiry = entry
        if expiry > time.time():
            return value
        self._store.pop(key, None)
        return None

    def set(self, key: str, value: Any):
        self._store[key] = (value, time.time() + self.ttl)

    def cleanup(self):
        """Remove all expired entries."""
        now = time.time()
        expired_keys = [k for k, (_, exp) in self._store.items() if exp <= now]
        for k in expired_keys:
            self._store.pop(k, None)


class RedisCache:
    def __init__(self, url: str, ttl_seconds: int = 300):
        if redis is None:
            raise RuntimeError("redis package is not installed")
        if ttl_seconds <= 0:
            raise ValueError("TTL must be a positive integer")
        self.client = redis.from_url(url)
        self.ttl = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        val = self.client.get(key)
        if val is None:
            return None
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return None

    def set(self, key: str, value: Any):
        self.client.setex(key, self.ttl, json.dumps(value))


def get_cache(ttl_seconds: int = 300):
    redis_url = os.environ.get("REDIS_URL")
    if redis_url:
        return RedisCache(redis_url, ttl_seconds=ttl_seconds)
    return TTLCache(ttl_seconds=ttl_seconds)
