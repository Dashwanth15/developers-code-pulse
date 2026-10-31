from fastapi import APIRouter

from app.api.v1.endpoints import (
    analytics,
    auth,
    bottlenecks,
    deployments,
    github,
    health,
    incidents,
    insights,
    organizations,
    pull_requests,
    reports,
    repositories,
)

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

# Analytics & Intelligence (Phase 3 & Phase 4 & Phase 7)
api_v1_router.include_router(analytics.router)

# Pull Request Lifecycle & Analytics (Phase 4)
api_v1_router.include_router(pull_requests.router)

# Bottleneck Detection Engine (Phase 6)
api_v1_router.include_router(bottlenecks.router)

# DORA Deployments & Releases (Phase 7)
api_v1_router.include_router(deployments.router)

# DORA Incidents & Outages (Phase 7)
api_v1_router.include_router(incidents.router)

# Reporting Engine (Phase 8)
api_v1_router.include_router(reports.router)

# AI Engineering Insights (Phase 8)
api_v1_router.include_router(insights.router)

