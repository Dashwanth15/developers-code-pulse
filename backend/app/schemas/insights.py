import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AIInsightBase(BaseModel):
    insight_type: str
    title: str
    explanation: str
    evidence: dict[str, Any] | None = None
    recommendation: str | None = None
    confidence: float = 1.0


class AIInsightCreateRequest(AIInsightBase):
    repository_id: uuid.UUID | None = None


class AIInsightGenerateRequest(BaseModel):
    repository_id: uuid.UUID | None = None
    time_range: str = Field(default="30d", description="7d, 14d, 30d, 90d")
    focus_areas: list[str] | None = Field(
        default=None,
        description="Optional list: ['throughput', 'bottlenecks', 'dora', 'collaboration']",
    )


class AIInsightResponse(AIInsightBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    repository_id: uuid.UUID | None
    provider: str
    model: str
    generated_at: datetime
    status: str
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AIInsightListResponse(BaseModel):
    items: list[AIInsightResponse]
    total: int
    executive_summary: str | None = None
    ai_provider_configured: bool = True
    provider_name: str = "gemini"
