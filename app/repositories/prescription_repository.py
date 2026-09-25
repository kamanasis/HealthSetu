"""Prescription and prescription item repositories.

DATABASE TEAM DEPENDENCY — PHASE 6
===================================
In-memory repository implementing the data contract for prescriptions and items.
Expected PostgreSQL tables:
- prescriptions
- prescription_items
"""

import asyncio
from datetime import datetime, timezone
import uuid
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from app.repositories.base import BaseRepository
from app.schemas.prescription import (
    NormalizationStatus,
    PrescriptionSource,
    PrescriptionStatus,
)


class PrescriptionItemRecord(BaseModel):
    """Database record representation of a prescription medication item."""
    model_config = ConfigDict(frozen=True)

    id: str
    prescription_id: str
    drug_name_raw: str
    strength_raw: str | None = None
    dosage_form_raw: str | None = None
    dose_raw: str | None = None
    route_raw: str | None = None
    frequency_raw: str | None = None
    duration_raw: str | None = None
    quantity_raw: str | None = None
    instructions_raw: str | None = None
    normalized_medication_id: str | None = None
    normalization_status: NormalizationStatus = NormalizationStatus.PENDING
    extraction_reference: str | None = None
    created_at: datetime
    updated_at: datetime


class PrescriptionRecord(BaseModel):
    """Database record representation of a prescription entity."""
    model_config = ConfigDict(frozen=True)

    id: str
    patient_id: str
    document_id: str | None = None
    extraction_id: str | None = None
    prescriber_reference: str | None = None
    prescription_date: datetime | None = None
    source: PrescriptionSource = PrescriptionSource.PATIENT_UPLOAD
    status: PrescriptionStatus = PrescriptionStatus.ACTIVE
    created_at: datetime
    updated_at: datetime


class PrescriptionRepository(BaseRepository[Any]):
    """Repository managing prescription entities and child items."""

    def __init__(self, session: Any = None) -> None:
        super().__init__(session=session)
        self._prescriptions: dict[str, PrescriptionRecord] = {}
        self._items: dict[str, PrescriptionItemRecord] = {}
        self._lock = asyncio.Lock()

    def clear(self) -> None:
        """Clear in-memory state for testing."""
        self._prescriptions.clear()
        self._items.clear()

    async def create_prescription(
        self, record: PrescriptionRecord, items: list[PrescriptionItemRecord]
    ) -> PrescriptionRecord:
        """Persist a new prescription and its initial medication items atomically."""
        async with self._lock:
            self._prescriptions[record.id] = record
            for item in items:
                self._items[item.id] = item
        return record

    async def get_prescription(self, prescription_id: str) -> PrescriptionRecord | None:
        """Fetch prescription by its primary key ID."""
        async with self._lock:
            return self._prescriptions.get(prescription_id)

    async def list_prescriptions(
        self, patient_id: str, skip: int = 0, limit: int = 20
    ) -> list[PrescriptionRecord]:
        """List prescriptions for a given patient, sorted by creation descending."""
        async with self._lock:
            patient_prescriptions = [
                p for p in self._prescriptions.values() if p.patient_id == patient_id
            ]
            patient_prescriptions.sort(key=lambda p: p.created_at, reverse=True)
            return patient_prescriptions[skip : skip + limit]

    async def count_prescriptions(self, patient_id: str) -> int:
        """Count total prescriptions for a patient."""
        async with self._lock:
            return sum(1 for p in self._prescriptions.values() if p.patient_id == patient_id)

    async def get_item(self, prescription_id: str, item_id: str) -> PrescriptionItemRecord | None:
        """Fetch a specific prescription item belonging to a prescription."""
        async with self._lock:
            item = self._items.get(item_id)
            if item and item.prescription_id == prescription_id:
                return item
            return None

    async def list_items(self, prescription_id: str) -> list[PrescriptionItemRecord]:
        """List all items belonging to a prescription."""
        async with self._lock:
            items = [item for item in self._items.values() if item.prescription_id == prescription_id]
            items.sort(key=lambda x: x.created_at)
            return items

    async def update_item_normalization(
        self,
        item_id: str,
        status: NormalizationStatus,
        normalized_medication_id: str | None = None,
    ) -> PrescriptionItemRecord | None:
        """Update normalization status and normalized medication link for an item."""
        async with self._lock:
            existing = self._items.get(item_id)
            if not existing:
                return None
            updated = existing.model_copy(
                update={
                    "normalization_status": status,
                    "normalized_medication_id": normalized_medication_id,
                    "updated_at": datetime.now(timezone.utc),
                }
            )
            self._items[item_id] = updated
            return updated

    async def update_prescription_status(
        self, prescription_id: str, new_status: PrescriptionStatus
    ) -> PrescriptionRecord | None:
        """Update prescription lifecycle status."""
        async with self._lock:
            existing = self._prescriptions.get(prescription_id)
            if not existing:
                return None
            updated = existing.model_copy(
                update={
                    "status": new_status,
                    "updated_at": datetime.now(timezone.utc),
                }
            )
            self._prescriptions[prescription_id] = updated
            return updated
