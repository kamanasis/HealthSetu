"""Mock Interoperability Provider (Phase 13).

In-memory provider adapter for local development and synthetic integration testing.
Does not require external credentials or live network endpoints.
"""

from datetime import datetime, timezone
from typing import Any
import uuid

from app.integrations.interoperability.base import InteroperabilityProvider


class MockInteroperabilityProvider(InteroperabilityProvider):
    """In-memory mock adapter simulating healthcare interoperability exchanges."""

    def __init__(self, name: str = "MockProvider") -> None:
        self.name = name
        self.sent_resources: list[dict[str, Any]] = []
        self.received_resources: list[dict[str, Any]] = []

    async def import_resource(
        self,
        source_system: str,
        resource_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Record and return incoming resource."""
        entry = {
            "source_system": source_system,
            "resource_type": resource_type,
            "payload": payload,
            "received_at": datetime.now(timezone.utc).isoformat(),
        }
        self.received_resources.append(entry)
        return payload

    async def export_resource(
        self,
        target_system: str,
        resource_payload: dict[str, Any],
        format: str = "FHIR",
    ) -> dict[str, Any]:
        """Simulate delivering resource to external partner system."""
        delivery_id = f"del-{uuid.uuid4().hex[:12]}"
        entry = {
            "delivery_id": delivery_id,
            "target_system": target_system,
            "format": format,
            "payload": resource_payload,
            "delivered_at": datetime.now(timezone.utc).isoformat(),
            "status": "DELIVERED",
        }
        self.sent_resources.append(entry)
        return {
            "status": "DELIVERED",
            "delivery_id": delivery_id,
            "target_system": target_system,
        }

    async def health_check(self) -> bool:
        """Always healthy in mock adapter."""
        return True
