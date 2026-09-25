"""HL7 v2 Message Parser (Phase 13).

Deterministic pipe-and-hat parser decomposing HL7 v2 messages into structured segments.
"""

from typing import Any


class HL7Parser:
    """Parses standard HL7 v2 raw text into segment dictionaries."""

    def parse(self, raw_message: str) -> dict[str, list[list[str]]]:
        """Parse HL7 text into map of segment_name -> list of fields."""
        segments: dict[str, list[list[str]]] = {}
        lines = [line.strip() for line in raw_message.strip().splitlines() if line.strip()]

        for line in lines:
            parts = line.split("|")
            seg_name = parts[0]
            if seg_name not in segments:
                segments[seg_name] = []
            segments[seg_name].append(parts[1:])

        return segments
