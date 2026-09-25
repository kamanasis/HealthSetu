"""Patient Transfer and Referral Repository (Phase 12).

DATABASE TEAM DEPENDENCY — PHASE 12
=====================================
Thread-safe in-memory repository implementing the data contract for patient transfers,
referrals, and attached clinical context snapshots.

Expected PostgreSQL tables:
- `transfers`
- `transfer_clinical_contexts`

See docs/phase-12-database-dependencies.md for full schema contract.
"""

import asyncio
from typing import Any

from app.repositories.base import BaseRepository
from app.schemas.transfer import TransferRecord, TransferStatus
from app.schemas.transfer_context import TransferClinicalContext


class TransferRepository(BaseRepository[TransferRecord]):
    """Thread-safe in-memory repository for patient transfers and clinical contexts."""

    def __init__(self, session: Any = None) -> None:
        super().__init__(session=session)
        # transfer_id -> TransferRecord
        self._transfers: dict[str, TransferRecord] = {}
        # patient_id -> list of transfer_ids
        self._patient_transfers: dict[str, list[str]] = {}
        # facility_id -> list of transfer_ids (both sending and receiving)
        self._facility_transfers: dict[str, list[str]] = {}
        # transfer_id -> TransferClinicalContext
        self._contexts: dict[str, TransferClinicalContext] = {}
        self._lock = asyncio.Lock()

    async def create(self, item: TransferRecord) -> TransferRecord:
        """Persist a new transfer request record."""
        async with self._lock:
            self._transfers[item.id] = item

            if item.patient_id not in self._patient_transfers:
                self._patient_transfers[item.patient_id] = []
            self._patient_transfers[item.patient_id].append(item.id)

            for fac_id in (item.sending_facility_id, item.receiving_facility_id):
                if fac_id not in self._facility_transfers:
                    self._facility_transfers[fac_id] = []
                if item.id not in self._facility_transfers[fac_id]:
                    self._facility_transfers[fac_id].append(item.id)

            return item

    async def get_by_id(self, id: str) -> TransferRecord | None:
        """Retrieve a transfer record by primary identifier."""
        async with self._lock:
            return self._transfers.get(id)

    async def update(self, id: str, item: TransferRecord) -> TransferRecord | None:
        """Update an existing transfer record."""
        async with self._lock:
            if id in self._transfers:
                self._transfers[id] = item
                return item
            return None

    async def list_by_patient(
        self,
        patient_id: str,
        limit: int = 50,
        offset: int = 0,
        status: TransferStatus | None = None,
    ) -> tuple[list[TransferRecord], int]:
        """List paginated transfers for a patient with optional status filter."""
        async with self._lock:
            transfer_ids = self._patient_transfers.get(patient_id, [])
            records: list[TransferRecord] = []
            for tid in transfer_ids:
                t = self._transfers.get(tid)
                if not t:
                    continue
                if status and t.status != status:
                    continue
                records.append(t)

            records.sort(key=lambda x: x.created_at, reverse=True)
            total = len(records)
            return records[offset: offset + limit], total

    async def list_by_facility(
        self,
        facility_id: str,
        limit: int = 50,
        offset: int = 0,
        status: TransferStatus | None = None,
    ) -> tuple[list[TransferRecord], int]:
        """List paginated transfers involving a specific facility."""
        async with self._lock:
            transfer_ids = self._facility_transfers.get(facility_id, [])
            records: list[TransferRecord] = []
            for tid in transfer_ids:
                t = self._transfers.get(tid)
                if not t:
                    continue
                if status and t.status != status:
                    continue
                records.append(t)

            records.sort(key=lambda x: x.created_at, reverse=True)
            total = len(records)
            return records[offset: offset + limit], total

    async def save_clinical_context(self, context: TransferClinicalContext) -> TransferClinicalContext:
        """Persist structured clinical context attached to a transfer."""
        async with self._lock:
            self._contexts[context.transfer_id] = context
            return context

    async def get_clinical_context(self, transfer_id: str) -> TransferClinicalContext | None:
        """Retrieve attached clinical context snapshot for a transfer."""
        async with self._lock:
            return self._contexts.get(transfer_id)

    def clear(self) -> None:
        """Clear all in-memory transfer state for test isolation."""
        self._transfers.clear()
        self._patient_transfers.clear()
        self._facility_transfers.clear()
        self._contexts.clear()
