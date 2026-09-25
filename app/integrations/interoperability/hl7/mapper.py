"""HL7 v2 Message Mapper (Phase 13).

Maps parsed HL7 segments (PID, OBR, OBX) into candidate data representations.
"""

from typing import Any


class HL7Mapper:
    """Mapper translating parsed HL7 segment structures to candidate representations."""

    MAPPER_VERSION = "1.0.0"

    def map_inbound_segments(self, segments: dict[str, list[list[str]]], source_system: str) -> dict[str, Any]:
        """Extract candidate patient and clinical data from parsed HL7 segments."""
        pid_segments = segments.get("PID", [])
        ext_patient_id = None
        patient_name = "Unknown"

        if pid_segments:
            pid_fields = pid_segments[0]
            # PID-3 is usually patient identifier list (index 2 in 0-indexed fields after segment name)
            if len(pid_fields) > 2:
                ext_patient_id = pid_fields[2].split("^")[0]
            # PID-5 is patient name (index 4)
            if len(pid_fields) > 4:
                patient_name = pid_fields[4].replace("^", " ").strip()

        return {
            "source_system": source_system,
            "external_patient_id": ext_patient_id,
            "patient_name": patient_name,
            "segments_parsed": list(segments.keys()),
            "mapper_version": self.MAPPER_VERSION,
        }
