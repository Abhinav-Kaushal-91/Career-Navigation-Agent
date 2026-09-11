"""Schema-constrained career-level synthesis over validated analysis objects."""

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ai_career_navigator.domain import (
    CandidateAccessibility,
    ConfidenceLevel,
    EvidenceMaturity,
    GapSeverity,
    RequirementFrequency,
)
from ai_career_navigator.models.output_text import unique_statements


class CareerSynthesisStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    SUCCEEDED_WITH_FALLBACK = "SUCCEEDED_WITH_FALLBACK"
    INSUFFICIENT = "INSUFFICIENT"


class AdvantageStrengthType(StrEnum):
    DIRECT = "DIRECT"
    TRANSFERABLE = "TRANSFERABLE"
    MIXED = "MIXED"


class TargetAlignmentType(StrEnum):
    DIRECTLY_ALIGNED = "DIRECTLY_ALIGNED"
    TRANSFERABLE = "TRANSFERABLE"
    PARTIALLY_ALIGNED = "PARTIALLY_ALIGNED"


class CareerGapDimension(StrEnum):
    FUNCTION = "FUNCTION"
    OWNERSHIP = "OWNERSHIP"
    SCOPE = "SCOPE"
    MATURITY = "MATURITY"
    TECHNICAL_DEPTH = "TECHNICAL_DEPTH"
    DOMAIN_DEPTH = "DOMAIN_DEPTH"
    PEOPLE_LEADERSHIP = "PEOPLE_LEADERSHIP"
    STRATEGIC_RESPONSIBILITY = "STRATEGIC_RESPONSIBILITY"
    LIFECYCLE_RESPONSIBILITY = "LIFECYCLE_RESPONSIBILITY"
    METRICS_OUTCOME_OWNERSHIP = "METRICS_OUTCOME_OWNERSHIP"
    PREREQUISITE = "PREREQUISITE"


class CareerAdvantageDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=100)
    explanation: str = Field(min_length=1, max_length=500)
    supporting_comparison_ids: list[UUID] = Field(min_length=1)
    supporting_evidence_ids: list[UUID] = Field(min_length=1)
    strength_type: AdvantageStrengthType


class TransferableStrengthDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_capability: str = Field(min_length=1, max_length=100)
    target_application: str = Field(min_length=1, max_length=100)
    explanation: str = Field(min_length=1, max_length=500)
    supporting_comparison_ids: list[UUID] = Field(min_length=1)
    supporting_evidence_ids: list[UUID] = Field(min_length=1)


class GroupedCareerGapDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=120)
    explanation: str = Field(min_length=1, max_length=600)
    underlying_gap_ids: list[UUID] = Field(min_length=1)
    what_candidate_already_has: str = Field(min_length=1, max_length=500)
    what_is_missing: str = Field(min_length=1, max_length=500)
    evidence_to_build: str = Field(min_length=1, max_length=500)


class CareerSynthesisDraft(BaseModel):
    """Model-editable semantic grouping without authority over policy fields."""

    model_config = ConfigDict(extra="forbid")

    strongest_advantages: list[CareerAdvantageDraft] = Field(default_factory=list, max_length=6)
    transferable_strengths: list[TransferableStrengthDraft] = Field(
        default_factory=list, max_length=6
    )
    grouped_gaps: list[GroupedCareerGapDraft] = Field(default_factory=list)
    assessment_summary: str = Field(min_length=1, max_length=900)
    limitations: list[str] = Field(default_factory=list, max_length=8)

    _unique_limitations = field_validator("limitations", mode="before")(unique_statements)


class CareerAdvantage(CareerAdvantageDraft):
    model_config = ConfigDict(frozen=True, extra="forbid")


class TransferableStrength(TransferableStrengthDraft):
    model_config = ConfigDict(frozen=True, extra="forbid")


class DemonstratedStrength(BaseModel):
    """Approved candidate evidence that remains visible regardless of target completeness."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str = Field(min_length=1, max_length=100)
    summary: str = Field(min_length=1, max_length=500)
    alignment_type: TargetAlignmentType
    target_requirements: list[str] = Field(min_length=1)
    supporting_comparison_ids: list[UUID] = Field(min_length=1)
    supporting_evidence_ids: list[UUID] = Field(min_length=1)
    maturity: EvidenceMaturity
    confidence: ConfidenceLevel


class TargetAlignment(BaseModel):
    """How demonstrated candidate evidence relates to one validated target requirement."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    candidate_capability: str = Field(min_length=1, max_length=160)
    target_requirement: str = Field(min_length=1, max_length=160)
    alignment_type: TargetAlignmentType
    what_candidate_has: str = Field(min_length=1, max_length=500)
    what_is_still_missing: str | None = Field(default=None, max_length=500)
    supporting_comparison_ids: list[UUID] = Field(min_length=1)
    supporting_evidence_ids: list[UUID] = Field(min_length=1)


class GroupedCareerGap(GroupedCareerGapDraft):
    model_config = ConfigDict(frozen=True, extra="forbid")

    severity: GapSeverity
    requirement_frequency: RequirementFrequency
    affected_requirement_ids: list[UUID] = Field(min_length=1)
    underlying_gap_count: int = Field(ge=1)
    high_or_blocking_gap_count: int = Field(ge=0)
    mandatory_requirement_count: int = Field(ge=0)
    preferred_requirement_count: int = Field(ge=0)
    display_title: str = Field(min_length=1, max_length=120)
    underlying_requirement_names: list[str] = Field(min_length=1)
    primary_dimension: CareerGapDimension
    affected_dimensions: list[CareerGapDimension] = Field(min_length=1)


class CareerAssessmentSynthesis(BaseModel):
    """Validated, auditable career-level interpretation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    target_role: str = Field(min_length=1)
    accessibility: CandidateAccessibility
    confidence: ConfidenceLevel
    demonstrated_strengths: list[DemonstratedStrength] = Field(default_factory=list, max_length=8)
    target_alignments: list[TargetAlignment] = Field(default_factory=list)
    strongest_advantages: list[CareerAdvantage] = Field(default_factory=list, max_length=6)
    transferable_strengths: list[TransferableStrength] = Field(default_factory=list, max_length=6)
    grouped_gaps: list[GroupedCareerGap] = Field(default_factory=list)
    assessment_summary: str = Field(min_length=1, max_length=900)
    accessibility_rationale: str = Field(min_length=1, max_length=900)
    source_comparison_ids: list[UUID] = Field(default_factory=list)
    source_gap_ids: list[UUID] = Field(default_factory=list)
    source_evidence_ids: list[UUID] = Field(default_factory=list)
    independent_severe_dimensions: list[CareerGapDimension] = Field(default_factory=list)
    direct_match_count: int = Field(ge=0)
    transferable_match_count: int = Field(ge=0)
    partial_match_count: int = Field(ge=0)
    partial_capability_present_count: int = Field(default=0, ge=0)
    partial_adjacent_count: int = Field(default=0, ge=0)
    partial_ownership_scope_count: int = Field(default=0, ge=0)
    no_confirmed_match_count: int = Field(ge=0)
    insufficient_comparison_count: int = Field(ge=0)
    raw_high_gap_count: int = Field(ge=0)
    raw_blocking_gap_count: int = Field(ge=0)
    limitations: list[str] = Field(default_factory=list)
    provider: str | None = None
    model: str | None = None
    prompt_version: str
    status: CareerSynthesisStatus
