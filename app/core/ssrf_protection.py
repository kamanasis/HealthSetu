"""SSRF protection utilities for HealthSetu.

SECURITY POLICY
================
Any backend-initiated outbound HTTP request to an external provider must pass
through the SSRF validator BEFORE the request is made.

This applies to ALL external integrations:
- AI providers (OpenAI, Azure OpenAI, etc.)
- OCR providers
- Medication terminology providers
- Medication safety providers
- Geolocation providers
- Healthcare directory providers
- Interoperability / FHIR server providers
- Object storage callbacks
- Any other external URL

BLOCKED ADDRESS CATEGORIES
===========================
- Loopback / localhost (127.0.0.1, ::1, localhost)
- Private IP ranges (RFC 1918: 10.x.x.x, 172.16-31.x.x, 192.168.x.x)
- Link-local addresses (169.254.x.x, fe80::/10)
- Cloud metadata endpoints (169.254.169.254, metadata.google.internal, etc.)
- Internal Kubernetes service addresses
- IPv6 special ranges

PRINCIPLE
==========
Fail CLOSED: if the URL cannot be safely validated, BLOCK the request.
Never accept client-provided external URLs without validation.
"""

from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urlparse

from app.core.exceptions import AppException, ErrorCode, SSRFBlockedException

# ---------------------------------------------------------------------------
# Blocked hostname patterns (case-insensitive)
# ---------------------------------------------------------------------------

_BLOCKED_HOSTNAME_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^localhost$", re.IGNORECASE),
    re.compile(r"^127\.", re.IGNORECASE),            # IPv4 loopback
    re.compile(r"^0\.0\.0\.0$"),                      # Null address
    re.compile(r"^::1$"),                              # IPv6 loopback
    re.compile(r"^::$"),                               # IPv6 null
    # Cloud metadata endpoints
    re.compile(r"169\.254\.169\.254"),                 # AWS/GCP/Azure instance metadata
    re.compile(r"metadata\.google\.internal", re.IGNORECASE),
    re.compile(r"metadata\.azure\.internal", re.IGNORECASE),
    re.compile(r"instance-data\.ec2\.internal", re.IGNORECASE),
    # Kubernetes internal DNS
    re.compile(r"\.svc\.cluster\.local$", re.IGNORECASE),
    re.compile(r"\.cluster\.local$", re.IGNORECASE),
    # Docker internal
    re.compile(r"^host\.docker\.internal$", re.IGNORECASE),
]

# ---------------------------------------------------------------------------
# Private IP ranges (RFC 1918 + link-local + CGNAT)
# ---------------------------------------------------------------------------

_PRIVATE_NETWORKS: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = [
    ipaddress.IPv4Network("10.0.0.0/8"),          # RFC 1918 Class A
    ipaddress.IPv4Network("172.16.0.0/12"),        # RFC 1918 Class B
    ipaddress.IPv4Network("192.168.0.0/16"),       # RFC 1918 Class C
    ipaddress.IPv4Network("127.0.0.0/8"),          # Loopback
    ipaddress.IPv4Network("169.254.0.0/16"),       # Link-local / APIPA
    ipaddress.IPv4Network("100.64.0.0/10"),        # CGNAT (RFC 6598)
    ipaddress.IPv4Network("0.0.0.0/8"),            # "This network"
    ipaddress.IPv4Network("198.51.100.0/24"),      # TEST-NET-2 (RFC 5737)
    ipaddress.IPv4Network("203.0.113.0/24"),       # TEST-NET-3 (RFC 5737)
    ipaddress.IPv4Network("240.0.0.0/4"),          # Reserved (RFC 1112)
    # IPv6
    ipaddress.IPv6Network("::1/128"),              # Loopback
    ipaddress.IPv6Network("fc00::/7"),             # ULA
    ipaddress.IPv6Network("fe80::/10"),            # Link-local
    ipaddress.IPv6Network("::ffff:0:0/96"),        # IPv4-mapped
]


def _is_private_ip(ip_str: str) -> bool:
    """Check whether an IP string is in any private/internal range."""
    try:
        addr = ipaddress.ip_address(ip_str)
        return any(addr in net for net in _PRIVATE_NETWORKS)
    except ValueError:
        # If we can't parse it, treat conservatively as blocked
        return True


def _resolve_and_check(hostname: str) -> bool:
    """Resolve hostname to IP(s) and check all resolved addresses.

    Returns True if the hostname is SAFE (all IPs are public).
    Returns False if any resolved IP is private/internal.

    Note: DNS resolution is performed for final validation.
    This is a defense-in-depth measure against DNS rebinding.
    """
    try:
        results = socket.getaddrinfo(hostname, None)
        for result in results:
            ip = result[4][0]
            if _is_private_ip(ip):
                return False
        return True
    except (socket.gaierror, OSError):
        # Cannot resolve — block it (fail closed)
        return False


def validate_external_url(
    url: str,
    *,
    allowed_schemes: tuple[str, ...] = ("https",),
    require_https: bool = True,
    resolve_dns: bool = True,
) -> str:
    """Validate that a URL is safe for backend-initiated external requests.

    Blocks:
    - Non-HTTPS schemes in production (http, file, gopher, ftp, etc.)
    - localhost / loopback
    - Private IP ranges (RFC 1918, link-local, CGNAT)
    - Cloud metadata endpoints
    - Kubernetes/Docker internal hostnames
    - URLs with no hostname

    Args:
        url: The URL to validate.
        allowed_schemes: Permitted URL schemes (default: https only).
        require_https: If True, non-https schemes are rejected.
        resolve_dns: If True, resolve the hostname to check all IPs.

    Returns:
        The validated URL (unchanged).

    Raises:
        SSRFBlockedException: If the URL is blocked.
        ValueError: If the URL is malformed.
    """
    if not url or not isinstance(url, str):
        raise SSRFBlockedException("External URL is empty or invalid.")

    url = url.strip()

    try:
        parsed = urlparse(url)
    except Exception:
        raise SSRFBlockedException("External URL could not be parsed.")

    # 1. Scheme check
    scheme = (parsed.scheme or "").lower()
    if scheme not in allowed_schemes:
        raise SSRFBlockedException(
            f"URL scheme '{scheme}' is not permitted. Allowed: {allowed_schemes}."
        )

    # 2. Hostname required
    hostname = parsed.hostname
    if not hostname:
        raise SSRFBlockedException("External URL has no hostname.")

    # 3. Block known internal hostnames by pattern
    for pattern in _BLOCKED_HOSTNAME_PATTERNS:
        if pattern.search(hostname):
            raise SSRFBlockedException(
                f"External URL hostname '{hostname}' resolves to a blocked internal address."
            )

    # 4. If hostname is a raw IP, check directly
    try:
        ip_obj = ipaddress.ip_address(hostname)
        if _is_private_ip(str(ip_obj)):
            raise SSRFBlockedException(
                f"External URL IP address '{hostname}' is in a private/internal range."
            )
        # Skip DNS resolution for raw IPs (already validated)
        return url
    except ValueError:
        pass  # hostname is a domain name — proceed to DNS check

    # 5. DNS resolution check (defense-in-depth against DNS rebinding)
    if resolve_dns:
        if not _resolve_and_check(hostname):
            raise SSRFBlockedException(
                f"External URL hostname '{hostname}' resolves to a private/internal IP address."
            )

    return url


def validate_provider_base_url(
    base_url: str,
    provider_name: str,
    *,
    allow_empty: bool = True,
) -> str | None:
    """Validate a provider base URL configuration value.

    Used to validate external provider base URLs at startup or at call time.
    Empty strings are accepted only when allow_empty=True (provider not configured).

    Args:
        base_url: The configured base URL for the external provider.
        provider_name: Human-readable provider name for error messages.
        allow_empty: If True, empty/unconfigured URLs are returned as None.

    Returns:
        Validated URL string or None if empty and allowed.

    Raises:
        SSRFBlockedException: If the URL is blocked.
        ValueError: If URL is required but missing.
    """
    if not base_url or base_url.strip() == "":
        if allow_empty:
            return None
        raise ValueError(f"Provider '{provider_name}' base URL is required but not configured.")

    return validate_external_url(base_url)
