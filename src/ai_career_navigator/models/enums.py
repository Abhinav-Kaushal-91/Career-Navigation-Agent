"""Provider-independent model classifications."""

from enum import StrEnum


class ModelRole(StrEnum):
    """Logical model responsibilities used by application code."""

    EXTRACTION = "EXTRACTION"
    REASONING = "REASONING"
    VALIDATION = "VALIDATION"
