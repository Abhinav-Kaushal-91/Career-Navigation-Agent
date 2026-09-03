"""Foundational UI design tokens.

No Streamlit rendering or custom CSS belongs in this Activity 3A module.
"""

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
