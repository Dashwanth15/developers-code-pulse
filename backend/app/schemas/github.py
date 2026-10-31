import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DiscoveredRepoResponse(BaseModel):
    """Repository discovered from GitHub API available for connection."""

    github_repo_id: int
    name: str
    full_name: str
    default_branch: str
    is_private: bool
    primary_language: str | None = None
    html_url: str
    is_connected: bool = False


class ConnectRepositoryRequest(BaseModel):
    """Request payload to connect an authorized repository to the organization."""

    github_repo_id: int
    name: str
    full_name: str
    default_branch: str = "main"
    is_private: bool = True
    primary_language: str | None = None


class ToggleMonitoringRequest(BaseModel):
    """Request payload to enable or pause repository monitoring."""

    is_monitored: bool


class RepositoryResponse(BaseModel):
    """Monitored repository metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    github_repo_id: int
    name: str
    full_name: str
    default_branch: str
    is_private: bool
    is_monitored: bool
    primary_language: str | None
    last_synced_at: datetime | None
    created_at: datetime


class WebhookIngestResponse(BaseModel):
    """Response returned upon webhook ingestion."""

    status: str = Field(..., description="'queued' or 'duplicate'")
    delivery_id: str
    event_type: str
    message: str
