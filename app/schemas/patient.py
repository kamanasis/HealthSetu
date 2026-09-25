"""Pydantic schemas for patient profile and patient identity.

Patient vs User distinction:
  USER  = authentication identity (Phase 2)
  PATIENT = clinical subject (Phase 4)

A patient may be linked to a user account, but the clinical record
uses a stable patient identifier — not the authentication user ID.

DATABASE TEAM DEPENDENCY — PHASE 4
====================================
Required patient entity fields:
  id               : Primary Key (UUID) — stable clinical identifier
  user_id          : NULLABLE FOREIGN KEY → users.id
  first_name       : VARCHAR
  last_name        : VARCHAR
  date_of_birth    : DATE (not timestamp)
  sex              : ENUM ('MALE', 'FEMALE', 'OTHER', 'UNKNOWN')
  preferred_language : NULLABLE VARCHAR (BCP-47 code, e.g. 'en', 'hi')
  phone            : NULLABLE VARCHAR
  email            : NULLABLE VARCHAR
  status           : ENUM ('ACTIVE', 'INACTIVE', 'MERGED', 'DELETED')
  created_at       : TIMESTAMP WITH TIME ZONE
  updated_at       : TIMESTAMP WITH TIME ZONE

PHI HANDLING:
  Patient name, date of birth, phone, and email are PHI.
  These fields must NEVER appear in:
    - access tokens (JWT)
    - request correlation IDs
    - application log messages
    - audit event payloads
    - URL paths (use opaque patient IDs)
"""

from datetime import date, datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class BiologicalSex(str, Enum):
    """Biological sex representation.

    DATABASE TEAM DEPENDENCY: align with actual database enum values.
    """
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class PatientStatus(str, Enum):
    """Patient record operational status."""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    MERGED = "MERGED"


class PatientResponse(BaseModel):
    """Public patient profile representation.

    Returns only the minimum fields required by the caller.
    PHI fields (name, DOB, phone, email) are included deliberately
    since this schema is only served to authorized callers.
    Never use this schema in log statements.
    """
    id: str = Field(description="Stable patient identifier")
    user_id: str | None = Field(default=None, description="Linked authentication user ID")
    first_name: str
    last_name: str
    date_of_birth: date
    sex: BiologicalSex
    preferred_language: str | None = None
    phone: str | None = None
    email: str | None = None
    status: PatientStatus
    created_at: datetime
    updated_at: datetime


class PatientSummary(BaseModel):
    """Minimal patient summary (non-PHI identifiers only).

    Used in contexts where full PHI response is not warranted,
    e.g., referencing a patient in a clinical history entry.
    """
    id: str
    status: PatientStatus


class PatientUpdateRequest(BaseModel):
    """PATCH request for updating permitted patient profile fields.

    Only explicitly provided fields are updated.
    Omitted fields remain unchanged (safe partial update).
    """
    model_config = ConfigDict(extra="forbid")

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    preferred_language: str | None = Field(default=None, max_length=10)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=255)
