"""Validated temporary input for deterministic career-goal capture."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ai_career_navigator.domain import GeographyScope, GoalType


def clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def conservative_unique(values: list[str]) -> list[str]:
    """Trim and deduplicate case-insensitively without semantic normalization."""

    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = value.strip()
        normalized = cleaned.casefold()
        if cleaned and normalized not in seen:
            seen.add(normalized)
            unique.append(cleaned)
    return unique


def normalize_preferences(values: list[str], no_preference_label: str) -> list[str]:
    unique = conservative_unique(values)
    if no_preference_label.casefold() in {value.casefold() for value in unique}:
        return [no_preference_label]
    return unique


class GoalDraft(BaseModel):
    """JSON-compatible goal input retained in temporary session state."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    goal_type: GoalType
    target_role: str | None = None
    target_seniority: str | None = None
    target_timeline_months: int | None = Field(default=None, gt=0)
    target_location: str | None = None
    target_industries: list[str] = Field(default_factory=list)
    preferred_work_modes: list[str] = Field(default_factory=list)
    geography_scopes: list[GeographyScope] = Field(default_factory=list)
    bridge_role_willingness: bool | None = None
    search_expansion_permission: bool = False
    exclusions: list[str] = Field(default_factory=list)

    _clean_target = field_validator("target_role", mode="before")(clean_optional)
    _clean_seniority = field_validator("target_seniority", mode="before")(clean_optional)
    _clean_location = field_validator("target_location", mode="before")(clean_optional)

    @field_validator("target_industries", mode="before")
    @classmethod
    def clean_industries(cls, value: list[str]) -> list[str]:
        return normalize_preferences(value, "No preference")

    @field_validator("preferred_work_modes", mode="before")
    @classmethod
    def clean_work_modes(cls, value: list[str]) -> list[str]:
        return normalize_preferences(value, "Flexible / No preference")

    @field_validator("exclusions", mode="before")
    @classmethod
    def clean_exclusions(cls, value: list[str]) -> list[str]:
        return conservative_unique(value)
