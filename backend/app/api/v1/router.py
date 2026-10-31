from fastapi import APIRouter

from app.api.v1.endpoints import auth, github, health, organizations, repositories

api_v1_router = APIRouter()

# System & Diagnostic Endpoints
api_v1_router.include_router(health.router)

# Authentication & User Management (Module 1)
api_v1_router.include_router(auth.router)

# Organization & Multi-Tenancy (Module 1)
api_v1_router.include_router(organizations.router)

# GitHub Integration & Webhooks (Module 2)
api_v1_router.include_router(github.router)

# Repository Management (Module 3)
api_v1_router.include_router(repositories.router)
