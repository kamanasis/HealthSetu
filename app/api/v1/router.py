"""API Version 1 Router."""

from fastapi import APIRouter
from app.api.v1.endpoints import (
    allergies,
    auth,
    clinical_history,
    consents,
    documents,
    encounters,
    health,
    medications,
    patients,
    prescriptions,
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


