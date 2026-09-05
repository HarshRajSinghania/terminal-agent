from limiter import SlidingWindowRateLimiter

def test_rate_limiter_allows_under_limit():
    limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=10.0)
    assert limiter.is_allowed("alice", current_time=100.0) is True
    assert limiter.is_allowed("alice", current_time=101.0) is True
    assert limiter.is_allowed("alice", current_time=102.0) is True

def test_rate_limiter_blocks_over_limit():
    limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=10.0)
    assert limiter.is_allowed("bob", current_time=100.0) is True
    assert limiter.is_allowed("bob", current_time=101.0) is True
    assert limiter.is_allowed("bob", current_time=102.0) is False

def test_rate_limiter_slides_window_and_recovers():
    limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=10.0)
    assert limiter.is_allowed("carol", current_time=100.0) is True
    assert limiter.is_allowed("carol", current_time=102.0) is True
    assert limiter.is_allowed("carol", current_time=105.0) is False
    # At t=111.0, the request at t=100.0 has expired
    assert limiter.is_allowed("carol", current_time=111.0) is True

