from app.core.config import get_settings
from app.services.ai.base import BaseAIProvider
from app.services.ai.deterministic_provider import DeterministicAIProvider
from app.services.ai.gemini_provider import GeminiAIProvider


def get_ai_provider() -> BaseAIProvider:
    """
    Factory function returning the configured AI insights provider.
    Defaults to Gemini if configured, or Deterministic engine.
    """
    settings = get_settings()
    if settings.AI_PROVIDER.lower() == "gemini" and settings.GEMINI_API_KEY:
        return GeminiAIProvider(
            api_key=settings.GEMINI_API_KEY,
            model=settings.GEMINI_MODEL,
        )
    return DeterministicAIProvider()
