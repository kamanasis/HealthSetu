"""Tests for CORS origin validation and HTTP security headers."""

from app.core.security import SECURITY_HEADERS, get_security_headers, is_origin_allowed


def test_is_origin_allowed():
    """Verify origin validation against allowlist."""
    allowed = ["https://app.healthsetu.com", "https://portal.healthsetu.com"]

    assert is_origin_allowed("https://app.healthsetu.com", allowed) is True
    assert is_origin_allowed("https://portal.healthsetu.com", allowed) is True
    assert is_origin_allowed("https://malicious-site.com", allowed) is False
    assert is_origin_allowed("http://app.healthsetu.com", allowed) is False
    assert is_origin_allowed("", allowed) is False
    assert is_origin_allowed("https://app.healthsetu.com/extra", allowed) is False


def test_is_origin_allowed_wildcard():
    """Verify that wildcard in allowed origins allows any origin."""
    assert is_origin_allowed("https://any-origin.org", ["*"]) is True


def test_security_headers_baseline():
    """Verify standard security headers are defined."""
    assert SECURITY_HEADERS["X-Content-Type-Options"] == "nosniff"
    assert SECURITY_HEADERS["X-Frame-Options"] == "DENY"
    assert SECURITY_HEADERS["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "Content-Security-Policy" in SECURITY_HEADERS
    assert "default-src 'self'" in SECURITY_HEADERS["Content-Security-Policy"]


def test_security_headers_production_hsts():
    """Verify HSTS header is added in production mode."""
    headers_dev = get_security_headers(is_production=False)
    assert "Strict-Transport-Security" not in headers_dev

    headers_prod = get_security_headers(is_production=True, enable_hsts=True)
    assert "Strict-Transport-Security" in headers_prod
    assert "max-age=31536000" in headers_prod["Strict-Transport-Security"]
