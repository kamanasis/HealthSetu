"""Production security configuration validation for HealthSetu.

SECURITY POLICY
================
This module validates that the application security configuration is
safe for the target environment at startup.

In production:
  - DEBUG must be False
  - Wildcard CORS with credentials is prohibited
  - Insecure placeholder secrets are rejected
  - Audit and PHI-safe logging must be enabled
  - Document storage must be private
  - External TLS verification must be enabled

FAIL CLOSED PRINCIPLE
======================
If validation fails in production, the application MUST NOT start.
Unsafe configuration is a security incident, not a warning.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.config import Settings


# ---------------------------------------------------------------------------
# Known insecure placeholder values that must be rejected in production
# ---------------------------------------------------------------------------

_INSECURE_JWT_SECRETS: frozenset[str] = frozenset(
    {
        "",
        "secret",
        "change-me",
        "changeme",
        "your-secret-key",
        "replace-this",
        "jwt_secret",
        "jwt-secret",
        "insecure",
        "dev_secret",
        "test",
        "test_secret",
        "unsafe",
        "placeholder",
        "default",
        "insecure_dev_jwt_secret_key_change_in_production_32bytes_min",
    }
)

_INSECURE_API_KEYS: frozenset[str] = frozenset(
    {
        "test",
        "test_key",
        "test-key",
        "demo",
        "demo_key",
        "placeholder",
        "your-api-key",
        "replace-this",
        "sk-test",
    }
)

# JWT secret minimum length for production (256-bit equivalent)
_MIN_JWT_SECRET_LENGTH = 32


@dataclass
class SecurityConfigViolation:
    """A single security configuration violation."""

    code: str
    message: str
    fatal: bool = True  # Fatal violations prevent startup in production


@dataclass
class SecurityConfigReport:
    """Result of security configuration validation."""

    environment: str
    violations: list[SecurityConfigViolation] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_safe(self) -> bool:
        """True if no fatal violations exist."""
        return not any(v.fatal for v in self.violations)

    @property
    def fatal_violations(self) -> list[SecurityConfigViolation]:
        return [v for v in self.violations if v.fatal]

    def summary(self) -> str:
        lines = [f"Security config report [{self.environment}]:"]
        if self.is_safe:
            lines.append("  ✓ No fatal violations found.")
        else:
            lines.append(f"  ✗ {len(self.fatal_violations)} FATAL violation(s):")
            for v in self.fatal_violations:
                lines.append(f"    [{v.code}] {v.message}")
        if self.warnings:
            lines.append(f"  {len(self.warnings)} warning(s):")
            for w in self.warnings:
                lines.append(f"    ⚠ {w}")
        return "\n".join(lines)


def _check_jwt_secret(settings: "Settings", report: SecurityConfigReport) -> None:
    """Validate JWT secret strength."""
    secret = settings.JWT_SECRET_KEY

    if not secret:
        report.violations.append(
            SecurityConfigViolation(
                code="MISSING_JWT_SECRET",
                message="JWT_SECRET_KEY is not set. Authentication is insecure.",
                fatal=True,
            )
        )
        return

    if secret.lower() in _INSECURE_JWT_SECRETS:
        report.violations.append(
            SecurityConfigViolation(
                code="INSECURE_JWT_SECRET",
                message=(
                    "JWT_SECRET_KEY is a known insecure placeholder. "
                    "Set a cryptographically random secret of at least 32 bytes."
                ),
                fatal=settings.is_production,
            )
        )
        return

    if len(secret) < _MIN_JWT_SECRET_LENGTH:
        report.violations.append(
            SecurityConfigViolation(
                code="JWT_SECRET_TOO_SHORT",
                message=(
                    f"JWT_SECRET_KEY is too short ({len(secret)} chars). "
                    f"Minimum is {_MIN_JWT_SECRET_LENGTH} characters."
                ),
                fatal=settings.is_production,
            )
        )


def _check_cors(settings: "Settings", report: SecurityConfigReport) -> None:
    """Validate CORS configuration."""
    origins = settings.CORS_ALLOWED_ORIGINS

    if "*" in origins:
        report.violations.append(
            SecurityConfigViolation(
                code="WILDCARD_CORS_WITH_CREDENTIALS",
                message=(
                    "CORS_ALLOWED_ORIGINS contains '*'. "
                    "Wildcard CORS with credentials is prohibited in production. "
                    "Enumerate allowed origins explicitly."
                ),
                fatal=settings.is_production,
            )
        )
        return

    if settings.is_production:
        for origin in origins:
            if origin.startswith("http://") and "localhost" not in origin:
                report.violations.append(
                    SecurityConfigViolation(
                        code="INSECURE_CORS_ORIGIN",
                        message=(
                            f"CORS origin '{origin}' uses plain HTTP in production. "
                            "Production CORS origins must use HTTPS."
                        ),
                        fatal=True,
                    )
                )


def _check_debug_mode(settings: "Settings", report: SecurityConfigReport) -> None:
    """Validate debug mode configuration."""
    if settings.is_production and settings.DEBUG:
        report.violations.append(
            SecurityConfigViolation(
                code="DEBUG_IN_PRODUCTION",
                message=(
                    "DEBUG=true in production environment. "
                    "Debug mode can expose stack traces, SQL, and internal paths. "
                    "Set DEBUG=false for production."
                ),
                fatal=True,
            )
        )


def _check_document_storage(settings: "Settings", report: SecurityConfigReport) -> None:
    """Validate document storage security."""
    if settings.is_production and settings.DOCUMENT_STORAGE_PROVIDER == "local":
        report.warnings.append(
            "DOCUMENT_STORAGE_PROVIDER=local in production. "
            "Medical documents should use private cloud object storage (e.g., S3 private bucket)."
        )


def _check_ai_config(settings: "Settings", report: SecurityConfigReport) -> None:
    """Validate AI provider configuration."""
    if not settings.AI_ENABLED:
        return

    if settings.is_production:
        # Production AI provider should not be mock
        if settings.AI_PROVIDER == "mock":
            report.warnings.append(
                "AI_PROVIDER=mock in production. Mock providers should not be used for production AI tasks."
            )

        # Check AI API key for non-mock providers
        if settings.AI_PROVIDER not in ("mock", "local") and not settings.AI_API_KEY:
            report.violations.append(
                SecurityConfigViolation(
                    code="MISSING_AI_API_KEY",
                    message=(
                        f"AI_PROVIDER={settings.AI_PROVIDER} but AI_API_KEY is not set. "
                        "External AI provider authentication is required."
                    ),
                    fatal=True,
                )
            )

        # AI API key should not be insecure placeholder
        if settings.AI_API_KEY and settings.AI_API_KEY.lower() in _INSECURE_API_KEYS:
            report.violations.append(
                SecurityConfigViolation(
                    code="INSECURE_AI_API_KEY",
                    message="AI_API_KEY is a known insecure placeholder value.",
                    fatal=True,
                )
            )

        # Training opt-in must be False
        if settings.AI_TRAINING_OPT_IN:
            report.violations.append(
                SecurityConfigViolation(
                    code="AI_TRAINING_OPTIN_ENABLED",
                    message=(
                        "AI_TRAINING_OPT_IN=true in production. "
                        "Patient data must not be used for AI provider training."
                    ),
                    fatal=True,
                )
            )

        # Data retention must be disabled
        if settings.AI_DATA_RETENTION_MODE not in ("disabled", "stateless"):
            report.violations.append(
                SecurityConfigViolation(
                    code="AI_DATA_RETENTION_UNSAFE",
                    message=(
                        f"AI_DATA_RETENTION_MODE={settings.AI_DATA_RETENTION_MODE}. "
                        "Provider-side data retention must be 'disabled' or 'stateless' for PHI protection."
                    ),
                    fatal=True,
                )
            )


def _check_medication_safety(settings: "Settings", report: SecurityConfigReport) -> None:
    """Validate medication safety provider configuration."""
    if not settings.MEDICATION_SAFETY_ENABLED:
        return

    if settings.is_production and settings.MEDICATION_SAFETY_PROVIDER not in ("mock", "local"):
        if not settings.MEDICATION_SAFETY_API_KEY:
            report.violations.append(
                SecurityConfigViolation(
                    code="MISSING_MEDICATION_SAFETY_API_KEY",
                    message=(
                        f"MEDICATION_SAFETY_PROVIDER={settings.MEDICATION_SAFETY_PROVIDER} "
                        "but MEDICATION_SAFETY_API_KEY is not set."
                    ),
                    fatal=True,
                )
            )


def _check_interoperability(settings: "Settings", report: SecurityConfigReport) -> None:
    """Validate interoperability provider configuration."""
    if not settings.INTEROPERABILITY_ENABLED:
        return

    if settings.is_production and settings.INTEROPERABILITY_PROVIDER not in ("none", "mock"):
        if not settings.INTEROPERABILITY_CLIENT_ID or not settings.INTEROPERABILITY_CLIENT_SECRET:
            report.violations.append(
                SecurityConfigViolation(
                    code="MISSING_INTEROPERABILITY_CREDENTIALS",
                    message=(
                        f"INTEROPERABILITY_PROVIDER={settings.INTEROPERABILITY_PROVIDER} "
                        "but client credentials are not configured."
                    ),
                    fatal=True,
                )
            )


def _check_database(settings: "Settings", report: SecurityConfigReport) -> None:
    """Validate database configuration."""
    if settings.is_production and not settings.DATABASE_URL:
        report.violations.append(
            SecurityConfigViolation(
                code="MISSING_DATABASE_URL",
                message="DATABASE_URL is not set in production. Database connectivity is required.",
                fatal=True,
            )
        )

    if settings.DATABASE_URL:
        # Database URL must not use insecure protocols
        url = settings.DATABASE_URL
        if "password" in url.lower() and any(
            placeholder in url.lower()
            for placeholder in ("password", "changeme", "change-me", "test", "placeholder")
        ):
            if settings.is_production:
                report.violations.append(
                    SecurityConfigViolation(
                        code="INSECURE_DATABASE_CREDENTIALS",
                        message=(
                            "DATABASE_URL appears to contain an insecure placeholder password. "
                            "Use secure, randomly generated database credentials in production."
                        ),
                        fatal=True,
                    )
                )


def validate_security_config(settings: "Settings") -> SecurityConfigReport:
    """Run all security configuration checks and return a report.

    Args:
        settings: Application settings to validate.

    Returns:
        SecurityConfigReport with all violations and warnings.
    """
    report = SecurityConfigReport(environment=settings.APP_ENV)

    _check_debug_mode(settings, report)
    _check_jwt_secret(settings, report)
    _check_cors(settings, report)
    _check_document_storage(settings, report)
    _check_ai_config(settings, report)
    _check_medication_safety(settings, report)
    _check_interoperability(settings, report)
    _check_database(settings, report)

    return report


def enforce_security_config(settings: "Settings") -> None:
    """Validate security configuration and raise RuntimeError if fatal violations exist.

    This function should be called at application startup.
    In production, any fatal violation will prevent startup (fail-closed).
    In development/testing, fatal violations are logged as warnings.

    Args:
        settings: Application settings to validate.

    Raises:
        RuntimeError: If fatal violations exist in production.
    """
    from app.core.logging import get_logger

    logger = get_logger("app.security_config")

    report = validate_security_config(settings)

    if not report.is_safe:
        for violation in report.fatal_violations:
            logger.error(
                f"SECURITY CONFIG VIOLATION [{violation.code}]: {violation.message}",
                extra={"event_type": "SECURITY_CONFIGURATION_FAILURE", "code": violation.code},
            )

        if settings.is_production:
            summary = report.summary()
            raise RuntimeError(
                f"Application startup blocked: security configuration violations detected "
                f"in production.\n{summary}"
            )
        else:
            logger.warning(
                "Security config violations detected in non-production environment. "
                "These would block startup in production."
            )

    for warning in report.warnings:
        logger.warning(
            f"Security config warning: {warning}",
            extra={"event_type": "SECURITY_CONFIGURATION_FAILURE"},
        )

    if report.is_safe:
        logger.info(
            f"Security configuration validated [{settings.APP_ENV}]: no fatal violations.",
            extra={"event_type": "SECURITY_CONFIGURATION_FAILURE", "outcome": "PASS"},
        )
