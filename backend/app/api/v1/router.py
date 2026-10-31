from fastapi import APIRouter

from app.api.v1.endpoints import health

api_v1_router = APIRouter()

# System & Diagnostic Endpoints
api_v1_router.include_router(health.router)
