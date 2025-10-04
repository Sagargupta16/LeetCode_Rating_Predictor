import time
import os
from typing import Any, Dict, Optional

try:
    import redis
except Exception:
    redis = None


class TTLCache:
    def __init__(self, ttl_seconds: int = 300):
        self.ttl = ttl_seconds
        self.store: Dict[str, Any] = {}
        self.expire: Dict[str, float] = {}

    def get(self, key: str) -> Optional[Any]:
        if key in self.store and self.expire.get(key, 0) > time.time():
            return self.store[key]
        if key in self.store:
            # expired
            self.store.pop(key, None)
            self.expire.pop(key, None)
        return None

    def set(self, key: str, value: Any):
        self.store[key] = value
        self.expire[key] = time.time() + self.ttl


class RedisCache:
    def __init__(self, url: str, ttl_seconds: int = 300):
        if redis is None:
            raise RuntimeError("redis package is not installed")
        self.client = redis.from_url(url)
        self.ttl = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        val = self.client.get(key)
        if val is None:
            return None
        try:
            import pickle

            return pickle.loads(val)
        except Exception:
            return None

    def set(self, key: str, value: Any):
        import pickle

        self.client.setex(key, self.ttl, pickle.dumps(value))


def get_cache(ttl_seconds: int = 300):
    redis_url = os.environ.get("REDIS_URL")
    if redis_url:
        return RedisCache(redis_url, ttl_seconds=ttl_seconds)
    return TTLCache(ttl_seconds=ttl_seconds)
