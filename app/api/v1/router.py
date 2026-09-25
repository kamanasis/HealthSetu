"""API Version 1 Router."""

from fastapi import APIRouter
from app.api.v1.endpoints import auth, health

v1_router = APIRouter()

# Register Phase 1 health and diagnostic endpoints
v1_router.include_router(health.router)

# Register Phase 2 identity & authentication endpoints
v1_router.include_router(auth.router)

# Future domain routers will be registered here in subsequent phases:
# - v1_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
# - v1_router.include_router(patient.router, prefix="/patients", tags=["Patients"])
# - v1_router.include_router(consent.router, prefix="/consent", tags=["Consent"])
# - v1_router.include_router(prescriptions.router, prefix="/prescriptions", tags=["Prescriptions"])
# - v1_router.include_router(triage.router, prefix="/triage", tags=["Triage"])
