"""Application configuration module using Pydantic Settings."""

from functools import lru_cache
from typing import Annotated, Literal
from pydantic import BeforeValidator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_cors_origins(v: str | list[str]) -> list[str]:
    """Parse CORS allowed origins from comma-separated string or list."""
    if isinstance(v, str):
        # Strip whitespace and trailing slashes for standard origin matching
        return [origin.strip().rstrip("/") for origin in v.split(",") if origin.strip()]
    if isinstance(v, list):
        return [origin.strip().rstrip("/") for origin in v if isinstance(origin, str) and origin.strip()]
    return []


CorsOrigins = Annotated[list[str], BeforeValidator(parse_cors_origins)]


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # General Application Info
    APP_NAME: str = Field(default="HealthSetu", description="Name of the application")
    APP_ENV: Literal["development", "testing", "production"] = Field(
        default="development",
        description="Application environment (development, testing, production)",
    )
    APP_VERSION: str = Field(default="0.1.0", description="Semantic version of application")
    DEBUG: bool = Field(default=False, description="Debug mode flag")
    HOST: str = Field(default="0.0.0.0", description="Host to bind server")
    PORT: int = Field(default=8000, description="Port to bind server")

    # Database Configuration (PostgreSQL Async Engine Layer)
    DATABASE_URL: str | None = Field(
        default=None,
        description="Async PostgreSQL connection URL (e.g., postgresql+asyncpg://user:pass@host:5432/db)",
    )

    # CORS Configuration
    CORS_ALLOWED_ORIGINS: CorsOrigins = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origins (comma-separated or list)",
    )

    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")

    # API Routing & Prefixes
    API_PREFIX: str = Field(default="/api/v1", description="Default API prefix")

    # Request Correlation
    REQUEST_ID_HEADER: str = Field(default="X-Request-ID", description="HTTP header key for request correlation ID")

    # Security & Request Limits
    MAX_REQUEST_SIZE_BYTES: int = Field(
        default=10 * 1024 * 1024,
        description="Maximum request payload size in bytes (default 10MB)",
    )

    # Authentication & JWT Configuration (Phase 2)
    JWT_SECRET_KEY: str = Field(
        default="insecure_dev_jwt_secret_key_change_in_production_32bytes_min",
        description="Cryptographic secret key for signing JWT tokens",
    )
    JWT_ALGORITHM: str = Field(
        default="HS256",
        description="JWT cryptographic algorithm (e.g. HS256, RS256)",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=15,
        description="Access token lifespan in minutes",
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=30,
        description="Refresh token lifespan in days",
    )
    PASSWORD_HASHING_SCHEME: str = Field(
        default="argon2id",
        description="Primary password hashing scheme",
    )
    AUTH_RATE_LIMIT_ENABLED: bool = Field(
        default=False,
        description="Flag enabling local/development authentication rate limiting hook",
    )

    # Document Processing Configuration (Phase 5)
    MAX_DOCUMENT_SIZE_MB: int = Field(
        default=20,
        description="Maximum allowed document upload size in megabytes",
    )
    MAX_DOCUMENT_PAGES: int = Field(
        default=50,
        description="Maximum allowed document page count for processing",
    )
    DOCUMENT_STORAGE_PROVIDER: str = Field(
        default="local",
        description="Object storage provider (local, s3, etc.)",
    )
    DOCUMENT_STORAGE_PATH: str = Field(
        default="data/documents",
        description="Filesystem root path for local document storage provider",
    )
    OCR_PROVIDER: str = Field(
        default="local",
        description="OCR provider implementation (local, cloud, mock)",
    )
    DOCUMENT_PROCESSING_ENABLED: bool = Field(
        default=True,
        description="Flag enabling background document processing pipeline",
    )
    MAX_PROCESSING_RETRIES: int = Field(
        default=3,
        description="Maximum automatic retry attempts for transient processing failures",
    )
    MALWARE_SCAN_ENABLED: bool = Field(
        default=False,
        description="Flag enabling malware security scanning hook",
    )
    OCR_TIMEOUT_SECONDS: int = Field(
        default=120,
        description="Maximum execution timeout for OCR extraction operations",
    )

    # Medication & Prescription Configuration (Phase 6)
    MEDICATION_TERMINOLOGY_PROVIDER: str = Field(
        default="local",
        description="Medication terminology provider ('local', 'rxnorm', 'licensed_provider')",
    )
    MEDICATION_TERMINOLOGY_BASE_URL: str = Field(
        default="",
        description="Base URL for external terminology provider API",
    )
    MEDICATION_TERMINOLOGY_API_KEY: str = Field(
        default="",
        description="Optional API key for external terminology provider",
    )
    MEDICATION_TERMINOLOGY_TIMEOUT_SECONDS: int = Field(
        default=10,
        description="Maximum execution timeout for terminology normalization calls",
    )
    MEDICATION_NORMALIZATION_ENABLED: bool = Field(
        default=True,
        description="Flag enabling medication normalization pipeline",
    )
    MEDICATION_NORMALIZATION_MAX_RETRIES: int = Field(
        default=2,
        description="Maximum retries for transient terminology provider failures",
    )

    # Medication Safety Configuration (Phase 7)
    MEDICATION_SAFETY_ENABLED: bool = Field(
        default=True,
        description="Flag enabling medication safety evaluation pipeline",
    )
    MEDICATION_SAFETY_PROVIDER: str = Field(
        default="mock",
        description="Medication safety provider ('mock', 'licensed_provider')",
    )
    MEDICATION_SAFETY_BASE_URL: str = Field(
        default="",
        description="Base URL for external licensed medication safety provider API",
    )
    MEDICATION_SAFETY_API_KEY: str = Field(
        default="",
        description="API key or token for external medication safety provider",
    )
    MEDICATION_SAFETY_TIMEOUT_SECONDS: int = Field(
        default=15,
        description="Maximum execution timeout in seconds for safety checks",
    )
    MEDICATION_SAFETY_MAX_RETRIES: int = Field(
        default=2,
        description="Maximum retry attempts for transient provider failures",
    )
    MEDICATION_SAFETY_RESULT_TTL_SECONDS: int = Field(
        default=3600,
        description="Maximum time-to-live for cached safety evaluations",
    )

    # Triage & SBAR Configuration (Phase 8)
    TRIAGE_ENABLED: bool = Field(
        default=True,
        description="Flag enabling clinical triage assessment pipeline",
    )
    TRIAGE_RULE_SET: str = Field(
        default="healthsetu_emergency_triage_v1",
        description="Active clinical triage protocol identifier",
    )
    TRIAGE_RULE_SET_VERSION: str = Field(
        default="1.0.0",
        description="Version string of the active triage protocol",
    )
    TRIAGE_RULE_ENGINE_TIMEOUT_SECONDS: int = Field(
        default=5,
        description="Maximum execution timeout in seconds for triage rule evaluation",
    )
    SBAR_ENABLED: bool = Field(
        default=True,
        description="Flag enabling SBAR clinical summary generation",
    )
    SBAR_GENERATION_MODE: str = Field(
        default="template",
        description="SBAR generation method: 'template' (deterministic) or 'ai'",
    )
    AI_PROVIDER: str = Field(
        default="mock",
        description="Clinical text generator provider ('mock', 'openai', 'anthropic', 'local')",
    )
    AI_BASE_URL: str = Field(
        default="",
        description="Base URL for external AI text generation provider",
    )
    AI_API_KEY: str = Field(
        default="",
        description="API key or token for external AI provider",
    )
    AI_TIMEOUT_SECONDS: int = Field(
        default=15,
        description="Timeout in seconds for AI text generation calls",
    )
    AI_MAX_OUTPUT_TOKENS: int = Field(
        default=1000,
        description="Maximum allowed output tokens for AI text generation",
    )

    # Care Plan & Discharge Configuration (Phase 9)
    CARE_PLAN_ENABLED: bool = Field(
        default=True,
        description="Flag enabling Care Plan and Discharge processing pipeline",
    )
    CARE_PLAN_DEFAULT_HORIZON_DAYS: int = Field(
        default=30,
        description="Default duration horizon in days for personalized care plans",
    )
    DISCHARGE_EXTRACTION_PROVIDER: str = Field(
        default="local",
        description="Provider for discharge instruction extraction ('local', 'mock', 'licensed')",
    )

    @property
    def max_document_size_bytes(self) -> int:
        """Maximum allowed document upload size in bytes."""
        return self.MAX_DOCUMENT_SIZE_MB * 1024 * 1024

    @property
    def is_production(self) -> bool:
        """Check if environment is production."""
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        """Check if environment is development."""
        return self.APP_ENV == "development"

    @property
    def is_testing(self) -> bool:
        """Check if environment is testing."""
        return self.APP_ENV == "testing"

    @property
    def docs_url(self) -> str | None:
        """OpenAPI Swagger UI documentation URL (accessible in dev/testing)."""
        return "/docs" if not self.is_production else None

    @property
    def redoc_url(self) -> str | None:
        """ReDoc documentation URL (accessible in dev/testing)."""
        return "/redoc" if not self.is_production else None

    @property
    def openapi_url(self) -> str | None:
        """OpenAPI schema JSON URL (accessible in dev/testing)."""
        return "/openapi.json" if not self.is_production else None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retrieve cached application settings instance."""
    return Settings()
