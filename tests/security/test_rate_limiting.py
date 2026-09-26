"""Tests for in-memory sliding window rate limiter."""

import pytest
import time
from app.core.rate_limiter import InMemoryRateLimiter, RateLimitConfig


def test_rate_limiter_allows_up_to_limit():
    """Verify that requests within configured limit are permitted."""
    limiter = InMemoryRateLimiter()
    config = RateLimitConfig(requests=3, window_seconds=60)
    key = "test_client_1"

    allowed1, remaining1, _ = limiter.is_allowed(key, config)
    assert allowed1 is True
    assert remaining1 == 2

    allowed2, remaining2, _ = limiter.is_allowed(key, config)
    assert allowed2 is True
    assert remaining2 == 1

    allowed3, remaining3, _ = limiter.is_allowed(key, config)
    assert allowed3 is True
    assert remaining3 == 0

    # 4th request exceeds limit
    allowed4, remaining4, retry_after = limiter.is_allowed(key, config)
    assert allowed4 is False
    assert remaining4 == 0
    assert retry_after > 0


def test_rate_limiter_keys_are_isolated():
    """Verify that limits for different clients/keys do not interfere."""
    limiter = InMemoryRateLimiter()
    config = RateLimitConfig(requests=1, window_seconds=60)

    # Client A consumes their limit
    allowed_a1, _, _ = limiter.is_allowed("client_a", config)
    assert allowed_a1 is True
    allowed_a2, _, _ = limiter.is_allowed("client_a", config)
    assert allowed_a2 is False

    # Client B should still be allowed
    allowed_b1, _, _ = limiter.is_allowed("client_b", config)
    assert allowed_b1 is True


def test_rate_limiter_reset():
    """Verify that resetting a key clears its history."""
    limiter = InMemoryRateLimiter()
    config = RateLimitConfig(requests=1, window_seconds=60)
    key = "client_to_reset"

    limiter.is_allowed(key, config)
    assert limiter.is_allowed(key, config)[0] is False

    limiter.reset(key)
    assert limiter.is_allowed(key, config)[0] is True
