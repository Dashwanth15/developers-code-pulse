import json
import logging
from typing import Any

import httpx

from app.core.config import get_settings
from app.services.ai.base import BaseAIProvider
from app.services.ai.deterministic_provider import DeterministicAIProvider

logger = logging.getLogger(__name__)


class GeminiAIProvider(BaseAIProvider):
    """
    Google Gemini AI Provider for synthesizing executive summaries and
    interpreting engineering flow telemetry.

    Adheres strictly to DCP's Anti-Surveillance Manifesto and Data Provenance:
    - Only receives pre-aggregated, anonymized organization metrics.
    - Zero individual developer scoring or personal rankings.
    - Grounded explanations based strictly on verified inputs.
    - Automatically falls back to DeterministicAIProvider if the external API is unreachable.
    """

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        self.fallback_provider = DeterministicAIProvider()

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def _call_gemini(self, system_prompt: str, user_prompt: str) -> str | None:
        if not self.is_available():
            return None

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": f"{system_prompt}\n\nTask:\n{user_prompt}"}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "topP": 0.8,
                "maxOutputTokens": 1500,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "").strip()
                else:
                    logger.warning(
                        "Gemini API returned status %s: %s",
                        response.status_code,
                        response.text[:200],
                    )
        except Exception as exc:
            logger.warning("Gemini API call failed with error: %s. Falling back to deterministic engine.", exc)

        return None

    async def generate_executive_summary(
        self,
        metrics_payload: dict[str, Any],
        organization_name: str,
        period_label: str,
    ) -> str:
        if not self.is_available():
            return await self.fallback_provider.generate_executive_summary(
                metrics_payload, organization_name, period_label
            )

        system_instruction = (
            "You are the Principal Engineering Intelligence Architect for Developers Code Pulse (DCP). "
            "Your role is to write an executive engineering summary analyzing macro software delivery telemetry.\n"
            "STRICT RULES:\n"
            "1. Ground all claims ONLY in the provided metrics. Do NOT invent or assume numbers.\n"
            "2. Never evaluate, rank, or mention individual developers (strict Anti-Surveillance Manifesto).\n"
            "3. If external CI/CD or incident data is absent, state that explicitly as INSUFFICIENT_DATA.\n"
            "4. Provide a clear, professional, executive-ready 2 to 3 paragraph summary."
        )

        user_content = (
            f"Organization: {organization_name}\n"
            f"Observation Window: {period_label}\n"
            f"Calculated Metrics Telemetry JSON:\n{json.dumps(metrics_payload, indent=2, default=str)}\n"
        )

        gemini_text = await self._call_gemini(system_instruction, user_content)
        if gemini_text:
            return gemini_text

        return await self.fallback_provider.generate_executive_summary(
            metrics_payload, organization_name, period_label
        )

    async def generate_insights(
        self,
        metrics_payload: dict[str, Any],
        organization_name: str,
        period_label: str,
        focus_areas: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        if not self.is_available():
            return await self.fallback_provider.generate_insights(
                metrics_payload, organization_name, period_label, focus_areas
            )

        system_instruction = (
            "You are the Lead Data Analytics Engineer for Developers Code Pulse. "
            "Analyze the provided software delivery telemetry and return a structured JSON list of actionable insights.\n"
            "STRICT REQUIREMENTS:\n"
            "1. Output MUST be valid JSON: an array of objects matching:\n"
            "   [{\"insight_type\": \"POSITIVE_TREND|DETERIORATING_TREND|WORKFLOW_BOTTLENECK|DORA_EVALUATION|HEALTH_DIAGNOSTIC\", "
            "\"title\": str, \"explanation\": str, \"evidence\": dict, \"recommendation\": str, \"confidence\": float}]\n"
            "2. Never fabricate metrics. Every explanation must cite exact numbers from the JSON.\n"
            "3. Zero individual developer rankings or performance judgements.\n"
            "4. Output ONLY the JSON array without markdown formatting or surrounding quotes if possible."
        )

        user_content = (
            f"Organization: {organization_name}\n"
            f"Period: {period_label}\n"
            f"Telemetry Data:\n{json.dumps(metrics_payload, indent=2, default=str)}\n"
        )

        gemini_text = await self._call_gemini(system_instruction, user_content)
        if gemini_text:
            try:
                clean_text = gemini_text.strip()
                if clean_text.startswith("```json"):
                    clean_text = clean_text[7:]
                if clean_text.startswith("```"):
                    clean_text = clean_text[3:]
                if clean_text.endswith("```"):
                    clean_text = clean_text[:-3]
                clean_text = clean_text.strip()
                parsed = json.loads(clean_text)
                if isinstance(parsed, list) and len(parsed) > 0:
                    return parsed
            except Exception as parse_err:
                logger.warning("Failed to parse Gemini structured JSON: %s. Using deterministic fallback.", parse_err)

        return await self.fallback_provider.generate_insights(
            metrics_payload, organization_name, period_label, focus_areas
        )
