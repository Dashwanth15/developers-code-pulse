from abc import ABC, abstractmethod
from typing import Any


class BaseAIProvider(ABC):
    """
    Abstract Base Class for AI Engineering Insights providers.
    Decouples the analytical reporting platform from specific foundation model vendors.
    """

    @abstractmethod
    async def generate_executive_summary(
        self,
        metrics_payload: dict[str, Any],
        organization_name: str,
        period_label: str,
    ) -> str:
        """Generate a synthesized executive summary from calculated metrics and evidence."""
        pass

    @abstractmethod
    async def generate_insights(
        self,
        metrics_payload: dict[str, Any],
        organization_name: str,
        period_label: str,
        focus_areas: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Generate structured, traceable insights (improvements, deteriorations,
        bottleneck prioritization, and evidence-backed recommendations).
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the provider is properly configured with credentials."""
        pass
