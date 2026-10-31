import abc
import hashlib
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.github import Repository


@dataclass
class DetectedBottleneck:
    """Standardized representation of a detected workflow bottleneck."""

    bottleneck_type: str
    severity: str
    confidence: str
    title: str
    description: str
    evidence: dict[str, Any]
    recommendation: str
    fingerprint: str
    observed_value: float
    baseline_value: float | None = None
    repository_id: uuid.UUID | None = None
    context: dict[str, Any] = field(default_factory=dict)


class BaseBottleneckDetector(abc.ABC):
    """Abstract base detector contract for engineering bottleneck identification."""

    bottleneck_type: str = "GENERIC_BOTTLENECK"

    @abc.abstractmethod
    async def detect(
        self,
        db: AsyncSession,
        organization_id: uuid.UUID,
        repository: Repository | None = None,
        time_window: str = "30d",
    ) -> list[DetectedBottleneck]:
        """Executes bottleneck detection against authorized tenant data."""
        pass

    def compute_fingerprint(
        self,
        organization_id: uuid.UUID,
        repository_id: uuid.UUID | None,
        target_key: str,
    ) -> str:
        """Generates a stable, unique fingerprint hash for idempotency and deduplication."""
        raw = f"{organization_id}:{repository_id or 'all'}:{self.bottleneck_type}:{target_key}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
