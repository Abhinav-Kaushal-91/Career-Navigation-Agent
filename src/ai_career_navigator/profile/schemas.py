"""Validated input schemas for structured manual profile onboarding."""

from datetime import date
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ai_career_navigator.domain import CareerStage, EvidenceMaturity
from ai_career_navigator.profile.capabilities import (
    clean_capability_name,
    dedupe_capabilities,
)


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _reasonable_year(value: int) -> int:
    earliest = date.today().year - 60
    latest = date.today().year + 15
    if not earliest <= value <= latest:
        raise ValueError(f"year must be between {earliest} and {latest}")
    return value


def _reasonable_optional_year(value: int | None) -> int | None:
    return None if value is None else _reasonable_year(value)


class SkillCategory(StrEnum):
    TECHNICAL = "Technical Skills"
    DOMAIN = "Domain / Business Knowledge"
    PROFESSIONAL = "Professional / Delivery Capabilities"
    LEADERSHIP = "Leadership / Scope"
    OTHER = "Other capability"


class ProjectType(StrEnum):
    PROFESSIONAL = "Professional project"
    PERSONAL = "Personal project"
    ACADEMIC = "Academic project"
    HACKATHON = "Hackathon"
    VOLUNTEER = "Volunteer project"
    OTHER = "Other achievement"


class ProjectStage(StrEnum):
    CONCEPT = "Concept"
    PROTOTYPE = "Prototype"
    MVP = "MVP"
    PILOT = "Pilot"
    PRODUCTION_GRADE = "Production-grade"


class AboutYou(BaseModel):
    model_config = ConfigDict(frozen=True)

    current_role: str | None = None
    years_professional_experience: float = Field(default=0, ge=0, le=80)
    current_location: str | None = None
    career_stage: CareerStage = CareerStage.OPEN_OTHER
    career_summary: str | None = None

    _clean_role = field_validator("current_role", mode="before")(_clean_optional)
    _clean_location = field_validator("current_location", mode="before")(_clean_optional)
    _clean_summary = field_validator("career_summary", mode="before")(_clean_optional)


class ExperienceEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    entry_id: UUID = Field(default_factory=uuid4)
    job_title: str = Field(min_length=1)
    organization: str = Field(min_length=1)
    start_date: date
    end_date: date | None = None
    current: bool = False
    location: str | None = None
    description: str | None = None
    accomplishments: list[str] = Field(default_factory=list)

    @field_validator("job_title", "organization")
    @classmethod
    def clean_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be blank")
        return cleaned

    _clean_location = field_validator("location", mode="before")(_clean_optional)
    _clean_description = field_validator("description", mode="before")(_clean_optional)

    @field_validator("accomplishments", mode="before")
    @classmethod
    def clean_accomplishments(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]

    @model_validator(mode="after")
    def validate_dates(self) -> "ExperienceEntry":
        today = date.today()
        earliest = date(today.year - 60, 1, 1)
        if self.start_date < earliest:
            raise ValueError(f"start date cannot be before {earliest.year}")
        if self.start_date > today:
            raise ValueError("start date cannot be in the future")
        if self.end_date and self.end_date > today:
            raise ValueError("end date cannot be in the future")
        if self.current and self.end_date is not None:
            raise ValueError("a current role must not have an end date")
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("end date cannot precede start date")
        return self


class SkillEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    entry_id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1)
    category: SkillCategory
    maturity: EvidenceMaturity

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned = clean_capability_name(value)
        if not cleaned:
            raise ValueError("skill name must not be blank")
        return cleaned


class ProjectEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    entry_id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1)
    project_type: ProjectType
    delivery_stage: ProjectStage = ProjectStage.PROTOTYPE
    context: str = Field(min_length=1)
    contribution: str = Field(min_length=1)
    capabilities_used: list[str] = Field(default_factory=list)
    maturity: EvidenceMaturity = EvidenceMaturity.DEMONSTRATED
    outcome: str = Field(min_length=1)
    measurable_impact: str | None = None

    @field_validator("name", "context", "contribution", "outcome")
    @classmethod
    def clean_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be blank")
        return cleaned

    @field_validator("capabilities_used", mode="before")
    @classmethod
    def clean_capabilities(cls, value: list[str]) -> list[str]:
        return list(dedupe_capabilities(value))

    _clean_impact = field_validator("measurable_impact", mode="before")(_clean_optional)


class EducationEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    entry_id: UUID = Field(default_factory=uuid4)
    qualification: str = Field(min_length=1)
    field_of_study: str | None = None
    institution: str = Field(min_length=1)
    completion_year: int
    expected: bool = False

    @field_validator("qualification", "institution")
    @classmethod
    def clean_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be blank")
        return cleaned

    _clean_field = field_validator("field_of_study", mode="before")(_clean_optional)
    _validate_year = field_validator("completion_year")(_reasonable_year)

    @model_validator(mode="after")
    def validate_future_completion(self) -> "EducationEntry":
        if self.completion_year > date.today().year and not self.expected:
            raise ValueError("a future completion year must be marked as expected")
        return self


class CertificationEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    entry_id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1)
    issuer: str = Field(min_length=1)
    year: int
    expiration_year: int | None = None

    @field_validator("name", "issuer")
    @classmethod
    def clean_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be blank")
        return cleaned

    _validate_year = field_validator("year")(_reasonable_year)
    _validate_expiration = field_validator("expiration_year")(_reasonable_optional_year)

    @model_validator(mode="after")
    def validate_expiration(self) -> "CertificationEntry":
        if self.year > date.today().year:
            raise ValueError("certification year cannot be in the future")
        if self.expiration_year is not None and self.expiration_year < self.year:
            raise ValueError("expiration year cannot precede certification year")
        return self


class ProfileDraft(BaseModel):
    """Complete temporary onboarding state before profile confirmation."""

    model_config = ConfigDict(frozen=True)

    about: AboutYou = Field(default_factory=AboutYou)
    experiences: list[ExperienceEntry] = Field(default_factory=list)
    core_competencies_text: str | None = None
    skills: list[SkillEntry] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)
    education: list[EducationEntry] = Field(default_factory=list)
    certifications: list[CertificationEntry] = Field(default_factory=list)

    _clean_core_competencies = field_validator("core_competencies_text", mode="before")(
        _clean_optional
    )
