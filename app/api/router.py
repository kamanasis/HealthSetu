"""Root API Router for HealthSetu supporting multiple API versions."""

from fastapi import APIRouter
from app.api.v1.router import v1_router

api_router = APIRouter()

# Mount API version 1 under /v1
api_router.include_router(v1_router, prefix="/v1")

# Future versions will be mounted here cleanly:
# api_router.include_router(v2_router, prefix="/v2")
