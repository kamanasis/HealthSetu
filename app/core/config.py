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
