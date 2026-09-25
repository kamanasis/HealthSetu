"""Interoperability Repository (Phase 13).

DATABASE TEAM DEPENDENCY — PHASE 13
===================================
In-memory repository implementing the data contract for external healthcare data
exchange tracking, external-to-internal identifier mapping, import records,
and export records.

Expected PostgreSQL tables:
- interoperability_imports
- interoperability_exports
- interoperability_patient_identifier_mappings
"""

import asyncio
from datetime import datetime, timezone
from typing import Any

from app.repositories.base import BaseRepository
from app.schemas.interoperability import (
    ExternalIdentifierMapping,
    InteroperabilityExportRecord,
    InteroperabilityImportRecord,
)


class InteroperabilityRepository(BaseRepository[Any]):
    """Thread-safe repository managing interoperability records and identity mappings."""

    def __init__(self, session: Any = None) -> None:
        super().__init__(session=session)
        self._imports: dict[str, InteroperabilityImportRecord] = {}
        self._exports: dict[str, InteroperabilityExportRecord] = {}
        # (source_system, external_patient_id) -> healthsetu_patient_id
        self._identity_mappings: dict[tuple[str, str], str] = {}
        # (source_system, external_resource_id) -> import_id (for idempotency)
        self._external_resource_index: dict[tuple[str, str], str] = {}
        self._lock = asyncio.Lock()

    async def create_import(self, record: InteroperabilityImportRecord) -> InteroperabilityImportRecord:
        """Persist a new interoperability import record."""
        async with self._lock:
            self._imports[record.id] = record
            idx_key = (record.source_system, record.external_resource_id)
            self._external_resource_index[idx_key] = record.id
            return record

    async def get_import(self, import_id: str) -> InteroperabilityImportRecord | None:
        """Fetch import record by unique ID."""
        async with self._lock:
            return self._imports.get(import_id)

    async def update_import(self, record: InteroperabilityImportRecord) -> InteroperabilityImportRecord:
        """Update existing import record (status, mapped data, verification)."""
        async with self._lock:
            record.updated_at = datetime.now(timezone.utc)
            self._imports[record.id] = record
            return record

    async def find_import_by_source_resource(
        self, source_system: str, external_resource_id: str
    ) -> InteroperabilityImportRecord | None:
        """Find existing import record by source system and external resource ID for idempotency."""
        async with self._lock:
            imp_id = self._external_resource_index.get((source_system, external_resource_id))
            if imp_id:
                return self._imports.get(imp_id)
            return None

    async def list_imports_by_patient(
        self, patient_id: str, limit: int = 50, offset: int = 0
    ) -> tuple[list[InteroperabilityImportRecord], int]:
        """List paginated import records associated with a HealthSetu patient."""
        async with self._lock:
            records = [
                r for r in self._imports.values()
                if r.healthsetu_patient_id == patient_id
            ]
            records.sort(key=lambda r: r.created_at, reverse=True)
            total = len(records)
            return records[offset : offset + limit], total

    async def create_export(self, record: InteroperabilityExportRecord) -> InteroperabilityExportRecord:
        """Persist a new interoperability export record."""
        async with self._lock:
            self._exports[record.id] = record
            return record

    async def get_export(self, export_id: str) -> InteroperabilityExportRecord | None:
        """Fetch export record by unique ID."""
        async with self._lock:
            return self._exports.get(export_id)

    async def list_exports_by_patient(
        self, patient_id: str, limit: int = 50, offset: int = 0
    ) -> tuple[list[InteroperabilityExportRecord], int]:
        """List paginated export records for a HealthSetu patient."""
        async with self._lock:
            records = [r for r in self._exports.values() if r.patient_id == patient_id]
            records.sort(key=lambda r: r.created_at, reverse=True)
            total = len(records)
            return records[offset : offset + limit], total

    async def map_identity(
        self, source_system: str, external_patient_id: str, healthsetu_patient_id: str
    ) -> None:
        """Save a deterministic external-to-HealthSetu patient identity mapping."""
        async with self._lock:
            self._identity_mappings[(source_system, external_patient_id)] = healthsetu_patient_id

    async def resolve_identity(self, source_system: str, external_patient_id: str) -> str | None:
        """Resolve HealthSetu patient ID from external source system and ID."""
        async with self._lock:
            return self._identity_mappings.get((source_system, external_patient_id))

    def clear(self) -> None:
        """Clear stored records (for unit and integration test isolation)."""
        self._imports.clear()
        self._exports.clear()
        self._identity_mappings.clear()
        self._external_resource_index.clear()
