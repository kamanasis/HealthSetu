"""Discharge instruction extractor integrations package (Phase 9)."""

from app.integrations.discharge.base import (
    DischargeExtractor,
    ExtractedDischargeData,
)
from app.integrations.discharge.extractor import LocalDischargeExtractor

__all__ = [
    "DischargeExtractor",
    "ExtractedDischargeData",
    "LocalDischargeExtractor",
]
