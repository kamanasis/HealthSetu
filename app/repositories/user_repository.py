"""User data access repository and database team contract definition.

DATABASE TEAM DEPENDENCY — PHASE 2
This repository defines the data access contract expected from the Database Team's
User/Identity entity:
- id: Primary Key (UUID / string)
- identifier: Unique string (e.g., email, phone, or username)
- password_hash: Argon2id hash string
- role: UserRole enum ('PATIENT', 'DOCTOR', 'ADMIN')
- status: AccountStatus enum ('ACTIVE', 'DISABLED', 'LOCKED', 'PENDING')
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base import BaseRepository
from app.schemas.auth import AccountStatus, UserRole


@dataclass
class UserRecord:
    """Contract representing a user identity record from the database."""

    id: str
    identifier: str
    password_hash: str
    role: UserRole
    status: AccountStatus
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UserRepository(BaseRepository[Any]):
    """Repository managing user identity and credential retrieval."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        super().__init__(session=session)  # type: ignore[arg-type]
        # In-memory registry fallback for development/testing prior to database team schema deployment
        self._local_users: dict[str, UserRecord] = {}

    def register_in_memory_user(self, user: UserRecord) -> None:
        """Register a user in memory for testing or local mocked development."""
        self._local_users[user.identifier.lower()] = user
        self._local_users[user.id] = user

    async def get_by_identifier(self, identifier: str) -> UserRecord | None:
        """Retrieve user identity by login identifier (email/phone/username).

        Case-insensitive match.
        """
        clean_id = identifier.strip().lower()
        if clean_id in self._local_users:
            return self._local_users[clean_id]

        # NOTE FOR DATABASE TEAM:
        # When SQLAlchemy User model is provided by the Database team:
        # if self.session:
        #     stmt = select(UserModel).where(func.lower(UserModel.identifier) == clean_id)
        #     result = await self.session.execute(stmt)
        #     model = result.scalar_one_or_none()
        #     return self._map_model_to_record(model) if model else None

        return None

    async def get_by_id(self, user_id: str) -> UserRecord | None:
        """Retrieve user identity by primary user ID."""
        if user_id in self._local_users:
            return self._local_users[user_id]

        # NOTE FOR DATABASE TEAM:
        # if self.session:
        #     stmt = select(UserModel).where(UserModel.id == user_id)
        #     result = await self.session.execute(stmt)
        #     model = result.scalar_one_or_none()
        #     return self._map_model_to_record(model) if model else None

        return None
