import time

from app.utils.cache import TTLCache


def test_ttl_cache_set_and_get():
    c = TTLCache(ttl_seconds=10)
    c.set("key1", {"foo": "bar"})
    assert c.get("key1") == {"foo": "bar"}


def test_ttl_cache_miss():
    c = TTLCache(ttl_seconds=10)
    assert c.get("nonexistent") is None


def test_ttl_cache_expiry():
    c = TTLCache(ttl_seconds=1)
    c.set("key1", "value1")
    assert c.get("key1") == "value1"
    time.sleep(1.1)
    assert c.get("key1") is None


def test_ttl_cache_overwrite():
    c = TTLCache(ttl_seconds=10)
    c.set("key1", "v1")
    c.set("key1", "v2")
    assert c.get("key1") == "v2"


def test_ttl_cache_cleanup():
    c = TTLCache(ttl_seconds=1)
    c.set("a", 1)
    c.set("b", 2)
    time.sleep(1.1)
    c.set("c", 3)
    c.cleanup()
    assert c.get("a") is None
    assert c.get("b") is None
    assert c.get("c") == 3


def test_ttl_cache_stores_various_types():
    c = TTLCache(ttl_seconds=10)
    c.set("int", 42)
    c.set("list", [1, 2, 3])
    c.set("nested", {"a": {"b": [1]}})
    assert c.get("int") == 42
    assert c.get("list") == [1, 2, 3]
    assert c.get("nested") == {"a": {"b": [1]}}


def test_ttl_cache_invalid_ttl():
    import pytest

    with pytest.raises(ValueError):
        TTLCache(ttl_seconds=0)
    with pytest.raises(ValueError):
        TTLCache(ttl_seconds=-5)
