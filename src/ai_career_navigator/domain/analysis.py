"""Candidate-to-role analysis schemas for V1."""

from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ai_career_navigator.domain.enums import (
    BridgeOutcome,
    CandidateAccessibility,
    ComparisonScope,
    ConfidenceLevel,
    EvidenceMaturity,
    FunctionalOverlap,
    GapCategory,
    GapSeverity,
    MatchType,
    MaturityAlignment,
    OwnershipAlignment,
    PartialMatchSubtype,
    ProductionContextDifference,
    RequirementFrequency,
    ScopeAlignment,
    TimelineClassification,
)


class RequirementComparison(BaseModel):
    """Comparison of one role requirement with confirmed candidate evidence."""

    model_config = ConfigDict(frozen=True)

    comparison_id: UUID = Field(default_factory=uuid4)
    requirement_id: UUID
    source_requirement_ids: list[UUID] = Field(default_factory=list)
    posting_id: UUID
    comparison_scope: ComparisonScope
    evidence_ids: list[UUID] = Field(default_factory=list)
    candidate_maturity: EvidenceMaturity | None = None
    target_maturity: EvidenceMaturity | None = None
    functional_overlap: FunctionalOverlap = FunctionalOverlap.NONE
    ownership_alignment: OwnershipAlignment = OwnershipAlignment.NOT_APPLICABLE
    scope_alignment: ScopeAlignment = ScopeAlignment.UNKNOWN
    maturity_alignment: MaturityAlignment = MaturityAlignment.UNKNOWN
    production_context_difference: ProductionContextDifference = ProductionContextDifference.UNKNOWN
    outcome_alignment: ScopeAlignment = ScopeAlignment.UNKNOWN
    evidence_status: Literal[
        "SUPPORTED", "UNKNOWN", "CONFIRMED_UNMET", "CONTRADICTED", "OPERATION_FAILED"
    ] = "UNKNOWN"
    clarification_needed: str | None = None
    validation_notes: list[str] = Field(default_factory=list)
    selected_evidence_ids: list[UUID] = Field(default_factory=list)
    omitted_evidence_ids: list[UUID] = Field(default_factory=list)
    grounded_evidence_quotes: list[dict[str, str]] = Field(default_factory=list)
    matched_alternative: str | None = None
    partial_match_subtype: PartialMatchSubtype | None = None
    match_type: MatchType | None
    transferable_capability: str | None = None
    remaining_difference: str | None = None
    explanation: str | None = None
    confidence: ConfidenceLevel


class GapItem(BaseModel):
    """A categorized difference between candidate evidence and role expectation."""

    model_config = ConfigDict(frozen=True)

    gap_id: UUID = Field(default_factory=uuid4)
    requirement_id: UUID
    requirement_ids: list[UUID] = Field(default_factory=list)
    source_requirement_ids: list[UUID] = Field(default_factory=list)
    comparison_scope: ComparisonScope
    requirement_frequency: RequirementFrequency
    category: GapCategory
    current_evidence_ids: list[UUID] = Field(default_factory=list)
    current_maturity: EvidenceMaturity | None = None
    target_expectation: str = Field(min_length=1)
    remaining_difference: str = Field(min_length=1)
    severity: GapSeverity
    hard_blocker: bool = False
    required_status: Literal["MANDATORY", "PREFERRED", "UNSPECIFIED"] = "UNSPECIFIED"
    employer_specific: bool = False
    evidence_status: Literal[
        "SUPPORTED", "UNKNOWN", "CONFIRMED_UNMET", "CONTRADICTED", "OPERATION_FAILED"
    ] = "UNKNOWN"
    clarification_needed: str | None = None
    evidence_needed: str | None = None
    possible_action: str | None = None
    confidence: ConfidenceLevel


class RoleAssessment(BaseModel):
    """A V1 conclusion about candidate accessibility to one role."""

    model_config = ConfigDict(frozen=True)

    role_assessment_id: UUID = Field(default_factory=uuid4)
    target_role: str = Field(min_length=1)
    requirement_comparisons: list[RequirementComparison] = Field(default_factory=list)
    gaps: list[GapItem] = Field(default_factory=list)
    candidate_accessibility: CandidateAccessibility
    explanation: str = Field(min_length=1)
    confidence: ConfidenceLevel
    source_ids: list[UUID] = Field(default_factory=list)


class BridgeRoleAssessment(BaseModel):
    """Evidence-based assessment of an optional intermediate role."""

    model_config = ConfigDict(frozen=True)

    bridge_assessment_id: UUID = Field(default_factory=uuid4)
    bridge_role: str | None = None
    current_strength_overlap: list[str] = Field(default_factory=list)
    gaps_reduced: list[str] = Field(default_factory=list)
    target_capabilities_gained: list[str] = Field(default_factory=list)
    market_availability_summary: str | None = None
    candidate_accessibility: CandidateAccessibility
    evidence_building_value: str | None = None
    leadership_scope_gain: str | None = None
    user_constraint_fit: str | None = None
    blockers: list[str] = Field(default_factory=list)
    outcome: BridgeOutcome
    explanation: str = Field(min_length=1)
    confidence: ConfidenceLevel


class TimelineAssessment(BaseModel):
    """Feasibility assessment for the user's requested timeline."""

    model_config = ConfigDict(frozen=True)

    timeline_assessment_id: UUID = Field(default_factory=uuid4)
    requested_months: int | None = Field(default=None, gt=0)
    classification: TimelineClassification
    assumptions: list[str] = Field(default_factory=list)
    blocking_gap_ids: list[UUID] = Field(default_factory=list)
    required_milestones: list[str] = Field(default_factory=list)
    bridge_role_required: bool = False
    market_dependencies: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel
    evidence_limitations: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_requested_timeline(self) -> "TimelineAssessment":
        if self.requested_months is None and self.classification not in {
            TimelineClassification.NO_FIXED_TIMELINE,
            TimelineClassification.UNSUPPORTED_INSUFFICIENT_EVIDENCE,
        }:
            raise ValueError("requested_months is required for a supported timeline assessment")
        return self
