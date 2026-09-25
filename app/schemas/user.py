"""Pydantic schemas for user identity and context representation."""

from pydantic import BaseModel, Field
from app.schemas.auth import AccountStatus, UserRole


class UserIdentityResponse(BaseModel):
    """User profile data returned by /auth/me."""

    id: str = Field(description="Unique user identifier")
    role: UserRole = Field(description="User primary role")
    status: AccountStatus = Field(description="Account operational status")


class AuthenticatedUserContext(BaseModel):
    """Lightweight backend context representing the authenticated caller.

    IMPORTANT: Contains NO clinical data (diagnoses, prescriptions, history).
    """

    user_id: str
    role: UserRole
    account_status: AccountStatus

    @property
    def is_active(self) -> bool:
        """Check if caller account is in active status."""
        return self.account_status == AccountStatus.ACTIVE
