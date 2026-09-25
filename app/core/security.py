"""Security utilities and boundary definitions for HealthSetu.

NOTE FOR PHASE 1:
Authentication (JWT, OAuth) and Authorization (RBAC, ABAC) belong to Phase 2.
No fake or mock authentication should be introduced in Phase 1.
"""

# Baseline secure headers configuration
SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=(), payment=()",
}


def is_origin_allowed(origin: str, allowed_origins: list[str]) -> bool:
    """Validate whether an incoming origin is in the allowed list."""
    if not origin:
        return False
    clean_origin = origin.strip().rstrip("/")
    return clean_origin in allowed_origins or "*" in allowed_origins
