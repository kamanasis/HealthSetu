"""Consent data access repository and database team contract definition.

DATABASE TEAM DEPENDENCY — PHASE 3
====================================
This repository defines the data access contract expected from the Database
Team's consent-related entities.

Required Consent entity fields:
  id              : Primary Key (UUID / string)
  patient_id      : FOREIGN KEY → users.id (consent subject)
  grantee_id      : FOREIGN KEY → users.id (consent recipient — e.g., doctor)
  purpose         : VARCHAR / ENUM — matches ConsentPurpose values
  scope           : VARCHAR / ENUM — matches ConsentScope values
  status          : ENUM ('ACTIVE', 'REVOKED', 'EXPIRED', 'PENDING', 'DENIED')
  granted_at      : TIMESTAMP WITH TIME ZONE
  effective_from  : TIMESTAMP WITH TIME ZONE
  expires_at      : NULLABLE TIMESTAMP WITH TIME ZONE
  revoked_at      : NULLABLE TIMESTAMP WITH TIME ZONE
  revoked_by      : NULLABLE FOREIGN KEY → users.id
  version         : INTEGER DEFAULT 1
  notes           : NULLABLE VARCHAR (patient notes, non-clinical)
  created_at      : TIMESTAMP WITH TIME ZONE

Required indexes:
  - (patient_id, status) for active consent lookup
  - (patient_id, grantee_id, purpose, scope, status) for targeted checks
  - (grantee_id, status) for doctor's granted-consents view

Until the database team delivers these, this repository operates on an
in-memory store for development and testing.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base import BaseRepository
from app.schemas.authorization import ConsentStatus


@dataclass
class ConsentRecord:
    """Contract representing a consent record from the database."""

    id: str
    patient_id: str
    grantee_id: str
    purpose: str
    scope: str
    status: ConsentStatus
    granted_at: datetime
    effective_from: datetime
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    revoked_by: str | None = None
    version: int = 1
    notes: str | None = None

    @property
    def is_active(self) -> bool:
        """True only when status is ACTIVE and not yet expired."""
        if self.status != ConsentStatus.ACTIVE:
            return False
        now = datetime.now(timezone.utc)
        if self.effective_from > now:
            return False
        if self.expires_at is not None and self.expires_at <= now:
            return False
        return True


class ConsentRepository(BaseRepository[Any]):
    """Repository managing consent lifecycle data access.

    In-memory implementation serves as a functional placeholder until
    the Database Team delivers the production consent schema and models.
    Integration point comments are provided throughout.
    """

    def __init__(self, session: AsyncSession | None = None) -> None:
        super().__init__(session=session)  # type: ignore[arg-type]
        # In-memory stores (testing/dev fallback)
        self._consents: dict[str, ConsentRecord] = {}   # id → record

    # -----------------------------------------------------------------------
    # Write operations
    # -----------------------------------------------------------------------

    async def create_consent(self, record: ConsentRecord) -> ConsentRecord:
        """Persist a new consent record.

        NOTE FOR DATABASE TEAM:
        Replace with:
            async with self.session.begin():
                orm_obj = ConsentModel(**record_to_dict(record))
                self.session.add(orm_obj)
            return map_model_to_record(orm_obj)
        """
        self._consents[record.id] = record
        return record

    async def update_consent_status(
        self,
        consent_id: str,
        new_status: ConsentStatus,
        revoked_at: datetime | None = None,
        revoked_by: str | None = None,
    ) -> ConsentRecord | None:
        """Update consent status (primarily for revocation).

        NOTE FOR DATABASE TEAM:
        Replace with UPDATE statement using consent_id primary key.
        """
        record = self._consents.get(consent_id)
        if record is None:
            return None

        # Dataclass field mutation for in-memory store
        from dataclasses import replace
        updated = replace(
            record,
            status=new_status,
            revoked_at=revoked_at,
            revoked_by=revoked_by,
        )
        self._consents[consent_id] = updated
        return updated

    # -----------------------------------------------------------------------
    # Read operations
    # -----------------------------------------------------------------------

    async def get_by_id(self, consent_id: str) -> ConsentRecord | None:
        """Retrieve a consent record by its primary key.

        NOTE FOR DATABASE TEAM:
        Replace with:
            stmt = select(ConsentModel).where(ConsentModel.id == consent_id)
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()
            return map_model_to_record(model) if model else None
        """
        return self._consents.get(consent_id)

    async def get_active_consent(
        self,
        patient_id: str,
        grantee_id: str,
        purpose: str,
        scope: str,
    ) -> ConsentRecord | None:
        """Look up an ACTIVE consent matching all four dimensions.

        Returns the first valid active consent or None.

        NOTE FOR DATABASE TEAM:
        Replace with indexed query:
            stmt = select(ConsentModel).where(
                ConsentModel.patient_id == patient_id,
                ConsentModel.grantee_id == grantee_id,
                ConsentModel.purpose == purpose,
                ConsentModel.scope == scope,
                ConsentModel.status == 'ACTIVE',
                or_(ConsentModel.expires_at.is_(None),
                    ConsentModel.expires_at > func.now()),
                ConsentModel.effective_from <= func.now(),
            ).limit(1)
        """
        now = datetime.now(timezone.utc)
        for record in self._consents.values():
            if (
                record.patient_id == patient_id
                and record.grantee_id == grantee_id
                and record.purpose == purpose
                and record.scope == scope
                and record.status == ConsentStatus.ACTIVE
                and record.effective_from <= now
                and (record.expires_at is None or record.expires_at > now)
            ):
                return record
        return None

    async def list_by_patient(
        self,
        patient_id: str,
        status_filter: ConsentStatus | None = None,
    ) -> list[ConsentRecord]:
        """List consents where the patient is the subject.

        NOTE FOR DATABASE TEAM:
        Replace with indexed query on (patient_id, status).
        """
        results = [r for r in self._consents.values() if r.patient_id == patient_id]
        if status_filter is not None:
            results = [r for r in results if r.status == status_filter]
        return results

    async def list_by_grantee(
        self,
        grantee_id: str,
        status_filter: ConsentStatus | None = None,
    ) -> list[ConsentRecord]:
        """List consents where the grantee is the recipient.

        NOTE FOR DATABASE TEAM:
        Replace with indexed query on (grantee_id, status).
        """
        results = [r for r in self._consents.values() if r.grantee_id == grantee_id]
        if status_filter is not None:
            results = [r for r in results if r.status == status_filter]
        return results
