from cache import InMemoryCache

def test_cache_get_set():
    cache = InMemoryCache()
    cache.set("user:1", {"name": "Alice"})
    assert cache.get("user:1") == {"name": "Alice"}
    assert cache.get("user:2") is None

def test_cache_invalidation():
    cache = InMemoryCache()
    cache.set("session:abc", "token_123")
    assert cache.get("session:abc") == "token_123"
    assert cache.invalidate("session:abc") is True
    assert cache.get("session:abc") is None
    assert cache.invalidate("session:abc") is False

def test_cache_clear_prefix():
    cache = InMemoryCache()
    cache.set("post:1", "p1")
    cache.set("post:2", "p2")
    cache.set("user:1", "u1")

    evicted = cache.clear_prefix("post:")
    assert evicted == 2
    assert cache.get("post:1") is None
    assert cache.get("post:2") is None
    assert cache.get("user:1") == "u1"
