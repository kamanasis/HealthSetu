"""Auth session and refresh token data access repository.

DATABASE TEAM DEPENDENCY — PHASE 2
This repository defines the data access contract expected from the Database Team's
Refresh Session entity:
- id: Primary Key (UUID / string)
- user_id: Foreign Key -> User.id
- token_hash: SHA-256 digest string of the refresh token (Never plaintext!)
- expires_at: TIMESTAMP WITH TIME ZONE
- is_revoked: BOOLEAN (default False)
- replaced_by_session_id: Nullable Foreign Key -> RefreshSession.id (for rotation tracking)
- created_at: TIMESTAMP WITH TIME ZONE
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base import BaseRepository


@dataclass
class RefreshSessionRecord:
    """Contract representing a stored refresh session."""

    id: str
    user_id: str
    token_hash: str
    expires_at: datetime
    is_revoked: bool
    created_at: datetime
    replaced_by_session_id: str | None = None

    @property
    def is_expired(self) -> bool:
        """Check if session token has expired."""
        now = datetime.now(timezone.utc)
        exp = self.expires_at if self.expires_at.tzinfo else self.expires_at.replace(tzinfo=timezone.utc)
        return now >= exp

    @property
    def is_valid(self) -> bool:
        """Check if session is currently active, unrevoked, and unexpired."""
        return not self.is_revoked and not self.is_expired


class AuthSessionRepository(BaseRepository[Any]):
    """Repository managing refresh session lifecycle, rotation, and revocation."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        super().__init__(session=session)  # type: ignore[arg-type]
        # In-memory store fallback for testing and development prior to database schema delivery
        self._sessions_by_id: dict[str, RefreshSessionRecord] = {}
        self._sessions_by_hash: dict[str, RefreshSessionRecord] = {}

    async def create_session(
        self,
        user_id: str,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshSessionRecord:
        """Persist a new refresh token session with hashed token."""
        session_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc)

        record = RefreshSessionRecord(
            id=session_id,
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            is_revoked=False,
            created_at=created_at,
            replaced_by_session_id=None,
        )

        self._sessions_by_id[session_id] = record
        self._sessions_by_hash[token_hash] = record

        # NOTE FOR DATABASE TEAM:
        # if self.session:
        #     model = RefreshSessionModel(...)
        #     self.session.add(model)
        #     await self.session.commit()

        return record

    async def get_session_by_token_hash(self, token_hash: str) -> RefreshSessionRecord | None:
        """Retrieve a session by its SHA-256 token hash."""
        return self._sessions_by_hash.get(token_hash)

    async def revoke_session(self, session_id: str) -> bool:
        """Revoke a specific session."""
        session = self._sessions_by_id.get(session_id)
        if session:
            session.is_revoked = True
            return True
        return False

    async def rotate_session(
        self,
        old_session_id: str,
        user_id: str,
        new_token_hash: str,
        new_expires_at: datetime,
    ) -> RefreshSessionRecord:
        """Rotate a refresh token: revoke the old session and link to the new session."""
        new_session = await self.create_session(
            user_id=user_id,
            token_hash=new_token_hash,
            expires_at=new_expires_at,
        )

        old_session = self._sessions_by_id.get(old_session_id)
        if old_session:
            old_session.is_revoked = True
            old_session.replaced_by_session_id = new_session.id

        return new_session

    async def revoke_all_user_sessions(self, user_id: str) -> int:
        """Revoke all active sessions for a user (used on token reuse attack detection)."""
        revoked_count = 0
        for s in self._sessions_by_id.values():
            if s.user_id == user_id and not s.is_revoked:
                s.is_revoked = True
                revoked_count += 1
        return revoked_count
