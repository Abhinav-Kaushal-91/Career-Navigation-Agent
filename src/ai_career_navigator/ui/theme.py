"""Central design tokens and semantic presentation helpers."""

from types import MappingProxyType
from typing import Final

SPACING: Final = MappingProxyType(
    {
        "xs": 4,
        "sm": 8,
        "compact": 12,
        "md": 16,
        "lg": 24,
        "xl": 32,
        "section": 48,
    }
)

RADII: Final = MappingProxyType(
    {
        "small": 8,
        "medium": 12,
        "large": 16,
    }
)

SEMANTIC_STATES: Final = MappingProxyType(
    {
        "success": "Confirmed or completed",
        "warning": "Limitation or attention required",
        "critical": "Blocking failure or invalid state",
        "neutral": "Context without judgment",
        "information": "Guidance or current workflow state",
    }
)

BADGE_TONES: Final = MappingProxyType(
    {
        "HIGH": "success",
        "MODERATE": "information",
        "LOW": "warning",
        "INSUFFICIENT": "critical",
        "STRONG": "success",
        "LIMITED": "warning",
        "SPARSE": "warning",
        "INSUFFICIENT_EVIDENCE": "critical",
        "INFERRED_PENDING": "warning",
        "CONFIRMED_INFERENCE": "success",
        "REJECTED_INFERENCE": "critical",
        "APPLY_NOW": "success",
        "APPLY_SELECTIVELY": "information",
        "NEAR_TERM_TARGET": "warning",
        "ASPIRATIONAL": "warning",
        "POOR_FIT": "critical",
        "SKILL": "information",
        "EXPERIENCE": "warning",
        "LEADERSHIP_SCOPE": "neutral",
        "EVIDENCE": "information",
        "CREDENTIAL_PREREQUISITE": "neutral",
    }
)


def badge_tone(label: str) -> str:
    """Return a semantic tone without encoding meaning in color alone."""

    return BADGE_TONES.get(label.upper(), "neutral")
