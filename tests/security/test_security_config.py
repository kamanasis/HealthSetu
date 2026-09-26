"""Tests for security configuration validation and fail-closed startup."""

import pytest
from app.core.config import Settings
from app.core.security_config import (
    enforce_security_config,
    validate_security_config,
)


def _make_production_settings(**overrides) -> Settings:
    """Helper to create Settings instance simulating production."""
    base = {
        "APP_ENV": "production",
        "DEBUG": False,
        "JWT_SECRET_KEY": "a_very_strong_random_secret_key_at_least_32_characters_long",
        "CORS_ALLOWED_ORIGINS": ["https://app.healthsetu.com"],
        "DATABASE_URL": "postgresql+asyncpg://user:secure_pass_xyz@db.prod.internal:5432/healthsetu",
        "AI_ENABLED": True,
        "AI_PROVIDER": "openai",
        "AI_API_KEY": "sk-real_production_api_key_valid_entropy",
        "AI_TRAINING_OPT_IN": False,
        "AI_DATA_RETENTION_MODE": "disabled",
        "DOCUMENT_STORAGE_PROVIDER": "s3",
    }
    base.update(overrides)
    return Settings(**base)


def test_safe_production_config_passes():
    """Verify that a properly secured production config passes validation."""
    settings = _make_production_settings()
    report = validate_security_config(settings)
    assert report.is_safe
    assert len(report.fatal_violations) == 0
    # Must not raise
    enforce_security_config(settings)


def test_production_rejects_debug_mode():
    """Verify that DEBUG=True in production triggers a fatal violation."""
    settings = _make_production_settings(DEBUG=True)
    report = validate_security_config(settings)
    assert not report.is_safe
    assert any(v.code == "DEBUG_IN_PRODUCTION" for v in report.fatal_violations)

    with pytest.raises(RuntimeError, match="Application startup blocked"):
        enforce_security_config(settings)


def test_production_rejects_wildcard_cors():
    """Verify that wildcard CORS origin is fatal in production."""
    settings = _make_production_settings(CORS_ALLOWED_ORIGINS=["*"])
    report = validate_security_config(settings)
    assert not report.is_safe
    assert any(v.code == "WILDCARD_CORS_WITH_CREDENTIALS" for v in report.fatal_violations)

    with pytest.raises(RuntimeError, match="Application startup blocked"):
        enforce_security_config(settings)


def test_production_rejects_short_or_insecure_jwt_secret():
    """Verify that short or known placeholder JWT secrets are fatal in production."""
    settings_short = _make_production_settings(JWT_SECRET_KEY="too-short")
    report = validate_security_config(settings_short)
    assert not report.is_safe
    assert any(v.code == "JWT_SECRET_TOO_SHORT" for v in report.fatal_violations)

    settings_insecure = _make_production_settings(JWT_SECRET_KEY="changeme")
    report2 = validate_security_config(settings_insecure)
    assert not report2.is_safe
    assert any(v.code == "INSECURE_JWT_SECRET" for v in report2.fatal_violations)


def test_production_rejects_ai_training_opt_in():
    """Verify that AI_TRAINING_OPT_IN=True in production is strictly prohibited."""
    settings = _make_production_settings(AI_TRAINING_OPT_IN=True)
    report = validate_security_config(settings)
    assert not report.is_safe
    assert any(v.code == "AI_TRAINING_OPTIN_ENABLED" for v in report.fatal_violations)

    with pytest.raises(RuntimeError, match="Application startup blocked"):
        enforce_security_config(settings)


def test_development_allows_relaxed_startup():
    """Verify that non-production environments do not abort startup on violations."""
    dev_settings = Settings(
        APP_ENV="development",
        DEBUG=True,
        JWT_SECRET_KEY="short",
        CORS_ALLOWED_ORIGINS=["*"],
    )
    # enforce_security_config should NOT raise in development
    enforce_security_config(dev_settings)
