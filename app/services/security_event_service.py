"""Security event service for HealthSetu.

SEPARATION OF CONCERNS
========================
Application logs  → operational / debugging (app/core/logging.py)
Audit events      → accountability, access decisions (app/services/audit_service.py)
Security events   → authentication failures, SSRF blocks, suspicious activity (here)

Security events focus on threats, attack indicators, and system-level security
decisions. They are PHI-free and feed security monitoring pipelines.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from app.core.logging import get_logger, request_id_ctx_var

logger = get_logger("app.security_event_service")


class SecurityEventType(str, Enum):
    """Security event taxonomy for HealthSetu."""

    # Authentication events
    AUTH_LOGIN_SUCCESS = "AUTH_LOGIN_SUCCESS"
    AUTH_LOGIN_FAILED = "AUTH_LOGIN_FAILED"
    AUTH_LOGOUT = "AUTH_LOGOUT"
    AUTH_TOKEN_INVALID = "AUTH_TOKEN_INVALID"
    AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
    AUTH_TOKEN_REVOKED = "AUTH_TOKEN_REVOKED"
    AUTH_SESSION_INVALIDATED = "AUTH_SESSION_INVALIDATED"
    AUTH_CREDENTIAL_FAILURE = "AUTH_CREDENTIAL_FAILURE"

    # Authorization events
    AUTHZ_DENIED = "AUTHZ_DENIED"
    AUTHZ_PATIENT_ACCESS_DENIED = "AUTHZ_PATIENT_ACCESS_DENIED"
    AUTHZ_ORGANIZATION_ACCESS_DENIED = "AUTHZ_ORGANIZATION_ACCESS_DENIED"
    AUTHZ_FACILITY_ACCESS_DENIED = "AUTHZ_FACILITY_ACCESS_DENIED"
    AUTHZ_ENCOUNTER_ACCESS_DENIED = "AUTHZ_ENCOUNTER_ACCESS_DENIED"
    AUTHZ_PRIVILEGE_ESCALATION_ATTEMPT = "AUTHZ_PRIVILEGE_ESCALATION_ATTEMPT"

    # Consent events
    CONSENT_REQUIRED = "CONSENT_REQUIRED"
    CONSENT_INVALID = "CONSENT_INVALID"
    CONSENT_BYPASSED_ATTEMPT = "CONSENT_BYPASSED_ATTEMPT"

    # Rate limiting
    RATE_LIMIT_TRIGGERED = "RATE_LIMIT_TRIGGERED"
    RATE_LIMIT_EXCEEDED_AUTH = "RATE_LIMIT_EXCEEDED_AUTH"
    RATE_LIMIT_EXCEEDED_AI = "RATE_LIMIT_EXCEEDED_AI"
    RATE_LIMIT_EXCEEDED_DOCUMENT = "RATE_LIMIT_EXCEEDED_DOCUMENT"
    RATE_LIMIT_EXCEEDED_EXTERNAL = "RATE_LIMIT_EXCEEDED_EXTERNAL"

    # SSRF & external threats
    SSRF_BLOCKED = "SSRF_BLOCKED"
    SSRF_ATTEMPT_DETECTED = "SSRF_ATTEMPT_DETECTED"
    EXTERNAL_URL_REJECTED = "EXTERNAL_URL_REJECTED"

    # Input threats
    PROMPT_INJECTION_DETECTED = "PROMPT_INJECTION_DETECTED"
    SQL_INJECTION_ATTEMPT = "SQL_INJECTION_ATTEMPT"
    PATH_TRAVERSAL_ATTEMPT = "PATH_TRAVERSAL_ATTEMPT"
    MALICIOUS_FILE_DETECTED = "MALICIOUS_FILE_DETECTED"
    OVERSIZED_REQUEST = "OVERSIZED_REQUEST"
    INVALID_CONTENT_TYPE = "INVALID_CONTENT_TYPE"
    RESOURCE_ENUMERATION_ATTEMPT = "RESOURCE_ENUMERATION_ATTEMPT"

    # File security
    FILE_TYPE_REJECTED = "FILE_TYPE_REJECTED"
    FILE_SIZE_EXCEEDED = "FILE_SIZE_EXCEEDED"
    FILE_MAGIC_BYTES_MISMATCH = "FILE_MAGIC_BYTES_MISMATCH"
    MALWARE_SCAN_TRIGGERED = "MALWARE_SCAN_TRIGGERED"

    # Configuration & system
    SECURITY_CONFIGURATION_FAILURE = "SECURITY_CONFIGURATION_FAILURE"
    INSECURE_CONFIGURATION_DETECTED = "INSECURE_CONFIGURATION_DETECTED"
    STARTUP_SECURITY_CHECK_FAILED = "STARTUP_SECURITY_CHECK_FAILED"

    # External provider
    EXTERNAL_PROVIDER_AUTH_FAILURE = "EXTERNAL_PROVIDER_AUTH_FAILURE"
    EXTERNAL_PROVIDER_TLS_ERROR = "EXTERNAL_PROVIDER_TLS_ERROR"
    EXTERNAL_PROVIDER_TIMEOUT = "EXTERNAL_PROVIDER_TIMEOUT"

    # AI security
    AI_SECURITY_VIOLATION = "AI_SECURITY_VIOLATION"
    AI_TASK_UNAUTHORIZED = "AI_TASK_UNAUTHORIZED"
    AI_OUTPUT_REJECTED = "AI_OUTPUT_REJECTED"

    # Suspicious activity
    SUSPICIOUS_REQUEST = "SUSPICIOUS_REQUEST"
    BRUTE_FORCE_DETECTED = "BRUTE_FORCE_DETECTED"
    ID_PROBING_DETECTED = "ID_PROBING_DETECTED"


class SecurityEventSeverity(str, Enum):
    """Security event severity levels."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ---------------------------------------------------------------------------
# Severity mapping for event types
# ---------------------------------------------------------------------------

_EVENT_SEVERITY: dict[SecurityEventType, SecurityEventSeverity] = {
    SecurityEventType.AUTH_LOGIN_FAILED: SecurityEventSeverity.MEDIUM,
    SecurityEventType.AUTH_TOKEN_INVALID: SecurityEventSeverity.MEDIUM,
    SecurityEventType.AUTH_TOKEN_EXPIRED: SecurityEventSeverity.LOW,
    SecurityEventType.AUTH_TOKEN_REVOKED: SecurityEventSeverity.HIGH,
    SecurityEventType.AUTH_CREDENTIAL_FAILURE: SecurityEventSeverity.HIGH,
    SecurityEventType.AUTHZ_DENIED: SecurityEventSeverity.MEDIUM,
    SecurityEventType.AUTHZ_PATIENT_ACCESS_DENIED: SecurityEventSeverity.HIGH,
    SecurityEventType.AUTHZ_PRIVILEGE_ESCALATION_ATTEMPT: SecurityEventSeverity.CRITICAL,
    SecurityEventType.CONSENT_BYPASSED_ATTEMPT: SecurityEventSeverity.CRITICAL,
    SecurityEventType.RATE_LIMIT_TRIGGERED: SecurityEventSeverity.LOW,
    SecurityEventType.SSRF_BLOCKED: SecurityEventSeverity.HIGH,
    SecurityEventType.SSRF_ATTEMPT_DETECTED: SecurityEventSeverity.CRITICAL,
    SecurityEventType.PROMPT_INJECTION_DETECTED: SecurityEventSeverity.HIGH,
    SecurityEventType.SQL_INJECTION_ATTEMPT: SecurityEventSeverity.CRITICAL,
    SecurityEventType.PATH_TRAVERSAL_ATTEMPT: SecurityEventSeverity.HIGH,
    SecurityEventType.MALICIOUS_FILE_DETECTED: SecurityEventSeverity.HIGH,
    SecurityEventType.SECURITY_CONFIGURATION_FAILURE: SecurityEventSeverity.CRITICAL,
    SecurityEventType.BRUTE_FORCE_DETECTED: SecurityEventSeverity.CRITICAL,
    SecurityEventType.SUSPICIOUS_REQUEST: SecurityEventSeverity.MEDIUM,
}


def _get_severity(event_type: SecurityEventType) -> SecurityEventSeverity:
    return _EVENT_SEVERITY.get(event_type, SecurityEventSeverity.MEDIUM)


class SecurityEventService:
    """Service for recording security events and security monitoring metrics.

    Security events are PHI-free and focus on threat indicators:
    - Authentication failures
    - Authorization rejections
    - Rate limit violations
    - SSRF blocks
    - Injection attempts
    - Configuration violations

    PHI RULE: Security events must NEVER contain:
    - Patient records, clinical notes, documents
    - Prescription or medication content
    - AI prompt or AI output text
    - Passwords, tokens, or secrets
    """

    def __init__(self) -> None:
        # In-memory security metric counters (PHI-free, reset on restart)
        self._counters: dict[str, int] = {}

    def _increment(self, key: str) -> None:
        self._counters[key] = self._counters.get(key, 0) + 1

    def emit(
        self,
        event_type: SecurityEventType,
        *,
        actor_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        ip_address: str | None = None,
        endpoint: str | None = None,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Emit a security event.

        Logs the event with structured metadata (PHI-safe).
        Increments internal monitoring counters.

        Args:
            event_type: Type of security event.
            actor_id: ID of the actor involved (omit if not authenticated).
            resource_type: Type of resource targeted.
            resource_id: ID of resource targeted.
            ip_address: Requesting IP (safely logged — not PHI).
            endpoint: API endpoint path (no query params with PHI).
            reason: Human-readable reason/code (no PHI).
            metadata: Additional PHI-free metadata dict.
        """
        severity = _get_severity(event_type)
        request_id = request_id_ctx_var.get()

        # Build PHI-safe log entry
        log_entry: dict[str, Any] = {
            "event_type": event_type.value,
            "severity": severity.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if request_id:
            log_entry["request_id"] = request_id
        if actor_id:
            log_entry["actor_id"] = actor_id
        if resource_type:
            log_entry["resource_type"] = resource_type
        if resource_id:
            log_entry["resource_id"] = resource_id
        if ip_address:
            log_entry["ip_address"] = ip_address
        if endpoint:
            # Strip query string to avoid logging PHI in URLs
            log_entry["endpoint"] = endpoint.split("?")[0]
        if reason:
            log_entry["reason"] = reason
        if metadata:
            # Only scalar metadata values allowed; no clinical content
            log_entry["metadata"] = {
                k: v
                for k, v in metadata.items()
                if isinstance(v, (str, int, float, bool)) and k not in {
                    "password", "token", "secret", "api_key", "clinical", "phi"
                }
            }

        # Emit structured log at appropriate level
        if severity in (SecurityEventSeverity.CRITICAL, SecurityEventSeverity.HIGH):
            logger.warning(f"SECURITY EVENT: {event_type.value}", extra=log_entry)
        else:
            logger.info(f"SECURITY EVENT: {event_type.value}", extra=log_entry)

        # Increment monitoring counter
        counter_key = event_type.value
        self._increment(counter_key)

        return log_entry

    def get_metrics(self) -> dict[str, Any]:
        """Return current security metric counters.

        Returns PHI-free event counts suitable for monitoring endpoints.
        """
        return {
            "security_event_counts": dict(self._counters),
            "snapshot_at": datetime.now(timezone.utc).isoformat(),
        }

    # ---------------------------------------------------------------------------
    # Convenience methods for common security events
    # ---------------------------------------------------------------------------

    def auth_failed(
        self,
        reason: str,
        ip_address: str | None = None,
        endpoint: str | None = None,
    ) -> None:
        """Record an authentication failure."""
        self.emit(
            SecurityEventType.AUTH_LOGIN_FAILED,
            ip_address=ip_address,
            endpoint=endpoint,
            reason=reason,
        )

    def token_invalid(self, reason: str, endpoint: str | None = None) -> None:
        """Record an invalid token attempt."""
        self.emit(
            SecurityEventType.AUTH_TOKEN_INVALID,
            endpoint=endpoint,
            reason=reason,
        )

    def token_expired(self, endpoint: str | None = None) -> None:
        """Record an expired token."""
        self.emit(
            SecurityEventType.AUTH_TOKEN_EXPIRED,
            endpoint=endpoint,
            reason="Token has expired.",
        )

    def authz_denied(
        self,
        actor_id: str | None,
        resource_type: str,
        reason: str,
        endpoint: str | None = None,
    ) -> None:
        """Record an authorization denial."""
        self.emit(
            SecurityEventType.AUTHZ_DENIED,
            actor_id=actor_id,
            resource_type=resource_type,
            endpoint=endpoint,
            reason=reason,
        )

    def patient_access_denied(
        self,
        actor_id: str | None,
        patient_id: str,
        reason: str,
    ) -> None:
        """Record a patient-level access denial."""
        self.emit(
            SecurityEventType.AUTHZ_PATIENT_ACCESS_DENIED,
            actor_id=actor_id,
            resource_type="patient",
            resource_id=patient_id,
            reason=reason,
        )

    def rate_limit_exceeded(
        self,
        actor_id: str | None,
        endpoint: str,
        limit_type: str = "general",
    ) -> None:
        """Record a rate limit exceeded event."""
        event_map = {
            "auth": SecurityEventType.RATE_LIMIT_EXCEEDED_AUTH,
            "ai": SecurityEventType.RATE_LIMIT_EXCEEDED_AI,
            "document": SecurityEventType.RATE_LIMIT_EXCEEDED_DOCUMENT,
            "external": SecurityEventType.RATE_LIMIT_EXCEEDED_EXTERNAL,
        }
        event_type = event_map.get(limit_type, SecurityEventType.RATE_LIMIT_TRIGGERED)
        self.emit(
            event_type,
            actor_id=actor_id,
            endpoint=endpoint,
            reason=f"Rate limit exceeded: {limit_type}",
        )

    def ssrf_blocked(
        self,
        blocked_url: str | None,
        actor_id: str | None = None,
        endpoint: str | None = None,
    ) -> None:
        """Record an SSRF attempt that was blocked."""
        # Truncate URL to avoid accidentally logging sensitive path data
        safe_url = (blocked_url or "")[:100] if blocked_url else None
        self.emit(
            SecurityEventType.SSRF_BLOCKED,
            actor_id=actor_id,
            endpoint=endpoint,
            reason="SSRF: blocked request to private/disallowed address",
            metadata={"blocked_url_prefix": safe_url},
        )

    def prompt_injection_detected(
        self,
        actor_id: str | None,
        task_type: str | None = None,
    ) -> None:
        """Record a detected prompt injection attempt."""
        self.emit(
            SecurityEventType.PROMPT_INJECTION_DETECTED,
            actor_id=actor_id,
            resource_type="ai_task",
            reason="Prompt injection patterns detected in AI input",
            metadata={"task_type": task_type},
        )

    def path_traversal_detected(
        self,
        actor_id: str | None,
        endpoint: str | None = None,
    ) -> None:
        """Record a path traversal attempt."""
        self.emit(
            SecurityEventType.PATH_TRAVERSAL_ATTEMPT,
            actor_id=actor_id,
            endpoint=endpoint,
            reason="Path traversal sequence detected in request",
        )

    def file_rejected(
        self,
        actor_id: str | None,
        reason: str,
        filename_safe: str | None = None,
    ) -> None:
        """Record a file upload rejection."""
        self.emit(
            SecurityEventType.FILE_TYPE_REJECTED,
            actor_id=actor_id,
            resource_type="document",
            reason=reason,
            metadata={"filename_prefix": (filename_safe or "")[:32]},
        )

    def security_config_failure(self, code: str, message: str) -> None:
        """Record a security configuration failure."""
        self.emit(
            SecurityEventType.SECURITY_CONFIGURATION_FAILURE,
            reason=f"[{code}] {message}",
        )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_global_security_event_service: SecurityEventService | None = None


def get_security_event_service() -> SecurityEventService:
    """Return the module-level SecurityEventService singleton."""
    global _global_security_event_service
    if _global_security_event_service is None:
        _global_security_event_service = SecurityEventService()
    return _global_security_event_service
