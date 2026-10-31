from dataclasses import dataclass
from enum import StrEnum


class ConfidenceLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass(frozen=True)
class ConfidenceAssessment:
    level: ConfidenceLevel
    is_baseline_established: bool
    sample_size: int
    explanation: str


def evaluate_confidence(sample_size: int, minimum_baseline_threshold: int = 5) -> ConfidenceAssessment:
    """
    Evaluates statistical reliability of an observed bottleneck based on sample size.
    Where sample size is below minimum_baseline_threshold, flags as an operational
    threshold alert rather than a statistically established historical baseline.
    """
    if sample_size < minimum_baseline_threshold:
        return ConfidenceAssessment(
            level=ConfidenceLevel.LOW,
            is_baseline_established=False,
            sample_size=sample_size,
            explanation=(
                f"Small sample size ({sample_size} observed items). Flagged as an operational "
                f"threshold alert; statistical baseline requires at least {minimum_baseline_threshold} items."
            ),
        )

    if sample_size < 15:
        return ConfidenceAssessment(
            level=ConfidenceLevel.MEDIUM,
            is_baseline_established=True,
            sample_size=sample_size,
            explanation=(
                f"Moderate sample size ({sample_size} observed items) establishing a reliable "
                "operational pattern."
            ),
        )

    return ConfidenceAssessment(
        level=ConfidenceLevel.HIGH,
        is_baseline_established=True,
        sample_size=sample_size,
        explanation=(
            f"Robust sample size ({sample_size} observed items) confirming a persistent "
            "and statistically verified delivery trend."
        ),
    )
