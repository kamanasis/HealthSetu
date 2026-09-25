"""API Version 1 Router."""

from fastapi import APIRouter
from app.api.v1.endpoints import (
    allergies,
    auth,
    care_plans,
    clinical_history,
    consents,
    discharge,
    documents,
    encounters,
    health,
    medications,
    medication_safety,
    patients,
    prescriptions,
    sbar,
    symptoms,
    triage,
    vitals,
)

v1_router = APIRouter()

# Register Phase 1 health and diagnostic endpoints
v1_router.include_router(health.router)

# Register Phase 2 identity & authentication endpoints
v1_router.include_router(auth.router)

# Register Phase 3 consent management endpoints
v1_router.include_router(consents.router)

# Register Phase 4 patient clinical record endpoints
v1_router.include_router(patients.router)
v1_router.include_router(clinical_history.router)
v1_router.include_router(allergies.router)
v1_router.include_router(vitals.router)
v1_router.include_router(encounters.router)

# Register Phase 5 medical document endpoints
v1_router.include_router(documents.router)

# Register Phase 6 prescription and medication endpoints
v1_router.include_router(prescriptions.router)
v1_router.include_router(medications.router)

# Register Phase 7 medication safety endpoints
v1_router.include_router(medication_safety.router)

# Register Phase 8 triage and SBAR endpoints
v1_router.include_router(symptoms.router)
v1_router.include_router(triage.router)
v1_router.include_router(sbar.router)

# Register Phase 9 care plan and discharge endpoints
v1_router.include_router(discharge.router)
v1_router.include_router(care_plans.router)


