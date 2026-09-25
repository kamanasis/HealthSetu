"""Pydantic schemas for authentication requests, responses, and token envelopes."""

from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class UserRole(str, Enum):
    """Supported user identity roles in HealthSetu.

    Extensible for future specialized clinical or organizational roles.
    """

    PATIENT = "PATIENT"
    DOCTOR = "DOCTOR"
    ADMIN = "ADMIN"


class AccountStatus(str, Enum):
    """Account operational statuses."""

    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    LOCKED = "LOCKED"
    PENDING = "PENDING"


class LoginRequest(BaseModel):
    """User credentials login request schema.

    Supports generic identifier (email, phone, username) to avoid assumptions.
    """

    model_config = ConfigDict(extra="forbid")

    identifier: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Login identifier (email, username, or phone)",
        examples=["doctor@healthsetu.org"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password credential",
        examples=["SecurePassw0rd!123"],
    )


class RefreshTokenRequest(BaseModel):
    """Request schema to exchange refresh token for new access token."""

    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(
        ...,
        min_length=16,
        description="Cryptographically secure refresh token string",
    )


class LogoutRequest(BaseModel):
    """Request schema for terminating authenticated session."""

    model_config = ConfigDict(extra="forbid")

    refresh_token: str | None = Field(
        default=None,
        description="Refresh token to revoke (optional if user session is known)",
    )


class UserIdentitySummary(BaseModel):
    """Minimal identity summary returned inside token responses."""

    id: str = Field(description="Unique user identifier")
    role: UserRole = Field(description="User primary role")


class TokenResponseData(BaseModel):
    """Authenticated token payload structure."""

    access_token: str = Field(description="Short-lived JWT access token")
    refresh_token: str = Field(description="Longer-lived refresh token")
    token_type: str = Field(default="bearer", description="Token authorization type")
    expires_in: int = Field(description="Access token lifespan in seconds")
    user: UserIdentitySummary = Field(description="Authenticated user identity summary")


class LogoutResponseData(BaseModel):
    """Response payload for logout operation."""

    message: str = Field(default="Logged out successfully.")
