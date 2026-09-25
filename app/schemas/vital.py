"""Pydantic schemas for patient vital measurements.

IMPORTANT:
- Vitals are recorded as-measured. No clinical interpretation.
- Units are always required. No unit-less values accepted.
- Historical measurements are preserved (append-only semantics).
- No medical thresholds enforced by backend validation.
  (e.g., heart rate > X does NOT trigger any backend decision.)

DATABASE TEAM DEPENDENCY — PHASE 4
====================================
Required vital entity fields:
  id           : Primary Key (UUID)
  patient_id   : FOREIGN KEY → patients.id
  vital_type   : ENUM or VARCHAR (see VitalType)
  value        : DECIMAL or FLOAT
  unit         : VARCHAR (e.g., 'bpm', 'celsius', 'mmHg', 'kg', 'cm', '%')
  measured_at  : TIMESTAMP WITH TIME ZONE (when measurement was taken)
  source       : ENUM provenance type
  recorded_by  : NULLABLE VARCHAR (user_id of recorder)
  device_id    : NULLABLE VARCHAR (device/sensor identifier)
  notes        : NULLABLE TEXT
  created_at   : TIMESTAMP WITH TIME ZONE
"""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.clinical_history import ClinicalDataSource


class VitalType(str, Enum):
    """Supported vital measurement types.

    DATABASE TEAM DEPENDENCY: align with actual reference enum/table.
    """
    TEMPERATURE = "TEMPERATURE"
    HEART_RATE = "HEART_RATE"
    RESPIRATORY_RATE = "RESPIRATORY_RATE"
    BLOOD_PRESSURE_SYSTOLIC = "BLOOD_PRESSURE_SYSTOLIC"
    BLOOD_PRESSURE_DIASTOLIC = "BLOOD_PRESSURE_DIASTOLIC"
    OXYGEN_SATURATION = "OXYGEN_SATURATION"
    WEIGHT = "WEIGHT"
    HEIGHT = "HEIGHT"
    BMI = "BMI"
    GLUCOSE = "GLUCOSE"


# Canonical unit per vital type (not enforced as medical thresholds,
# only as data-integrity constraints: value must have a unit).
VITAL_CANONICAL_UNITS: dict[VitalType, list[str]] = {
    VitalType.TEMPERATURE:             ["celsius", "fahrenheit"],
    VitalType.HEART_RATE:              ["bpm"],
    VitalType.RESPIRATORY_RATE:        ["breaths_per_min"],
    VitalType.BLOOD_PRESSURE_SYSTOLIC: ["mmhg"],
    VitalType.BLOOD_PRESSURE_DIASTOLIC:["mmhg"],
    VitalType.OXYGEN_SATURATION:       ["%"],
    VitalType.WEIGHT:                  ["kg", "lbs"],
    VitalType.HEIGHT:                  ["cm", "m", "inches"],
    VitalType.BMI:                     ["kg/m2"],
    VitalType.GLUCOSE:                 ["mg/dl", "mmol/l"],
}


class VitalSource(str, Enum):
    """Source classification for a vital measurement."""
    PATIENT_REPORTED = "PATIENT_REPORTED"
    CLINIC_RECORDED = "CLINIC_RECORDED"
    DEVICE = "DEVICE"
    IMPORTED = "IMPORTED"
    UNKNOWN = "UNKNOWN"


class VitalCreateRequest(BaseModel):
    """Request body for recording a vital measurement.

    Unit is always required — no unitless measurements accepted.
    measured_at must be timezone-aware.
    """
    model_config = ConfigDict(extra="forbid")

    vital_type: VitalType = Field(description="Type of vital measurement")
    value: float = Field(
        ...,
        description="Numeric measurement value. Must be finite.",
        examples=[98.6, 72, 120],
    )
    unit: str = Field(
        ..., min_length=1, max_length=20,
        description="Measurement unit (e.g., 'celsius', 'bpm', 'mmHg'). Always required.",
        examples=["celsius", "bpm", "mmhg"],
    )
    measured_at: datetime = Field(
        description="UTC timestamp of when the measurement was taken. Must be timezone-aware.",
    )
    source: VitalSource = Field(
        default=VitalSource.PATIENT_REPORTED,
        description="Source classification for this measurement",
    )
    device_id: str | None = Field(
        default=None, max_length=255,
        description="Device or sensor identifier if measurement is device-sourced",
    )
    notes: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_unit_for_type(self) -> "VitalCreateRequest":
        """Validate that the provided unit is accepted for the vital type."""
        import math
        if math.isnan(self.value) or math.isinf(self.value):
            raise ValueError("Vital value must be a finite number.")
        accepted = VITAL_CANONICAL_UNITS.get(self.vital_type, [])
        if accepted and self.unit.lower() not in accepted:
            raise ValueError(
                f"Unit '{self.unit}' is not accepted for {self.vital_type.value}. "
                f"Accepted units: {accepted}"
            )
        if not self.measured_at.tzinfo:
            raise ValueError("measured_at must include timezone information (use UTC).")
        return self


class VitalResponse(BaseModel):
    """Public vital measurement record."""
    id: str
    patient_id: str
    vital_type: VitalType
    value: float
    unit: str
    measured_at: datetime
    source: VitalSource
    recorded_by: str | None = None
    device_id: str | None = None
    notes: str | None = None
    created_at: datetime


class VitalListResponse(BaseModel):
    items: list[VitalResponse]
    total: int
