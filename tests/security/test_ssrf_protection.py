"""Tests for Server-Side Request Forgery (SSRF) protection module."""

import pytest
from app.core.exceptions import SSRFBlockedException
from app.core.ssrf_protection import (
    validate_external_url,
    validate_provider_base_url,
)


@pytest.mark.parametrize(
    "blocked_url",
    [
        "http://localhost:8000/internal",
        "https://127.0.0.1:8000/api",
        "https://127.0.0.2/admin",
        "https://[::1]/status",
        "http://10.0.0.1/private",
        "https://192.168.1.100/router",
        "https://172.16.5.1/internal",
        "http://169.254.169.254/latest/meta-data/",
        "https://metadata.google.internal/computeMetadata/v1/",
        "file:///etc/passwd",
        "ftp://internal.server/file",
        "gopher://internal.server:70",
    ],
)
def test_ssrf_blocks_private_and_metadata_targets(blocked_url: str):
    """Verify that private IPs, cloud metadata, and forbidden schemes are blocked."""
    with pytest.raises(SSRFBlockedException):
        validate_external_url(blocked_url, resolve_dns=False)


def test_ssrf_allows_public_https_url():
    """Verify that standard public HTTPS endpoints are accepted."""
    url = "https://rxnav.nlm.nih.gov/REST/rxcui"
    validated = validate_external_url(url, resolve_dns=False)
    assert validated == url


def test_validate_provider_base_url_empty_allowed():
    """Verify that empty URLs are safely allowed when allow_empty=True."""
    assert validate_provider_base_url("", "test_provider", allow_empty=True) is None
    assert validate_provider_base_url("   ", "test_provider", allow_empty=True) is None


def test_validate_provider_base_url_empty_not_allowed():
    """Verify that missing URLs raise ValueError when allow_empty=False."""
    with pytest.raises(ValueError, match="required"):
        validate_provider_base_url("", "test_provider", allow_empty=False)


def test_validate_provider_base_url_blocks_internal():
    """Verify that internal provider URLs are blocked."""
    with pytest.raises(SSRFBlockedException):
        validate_provider_base_url("https://10.0.1.5:9000", "test_provider")
