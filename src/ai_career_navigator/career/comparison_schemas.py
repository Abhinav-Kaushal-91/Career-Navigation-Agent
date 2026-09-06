"""Provider-neutral schemas for requirement comparison."""

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ai_career_navigator.domain import (
    ConfidenceLevel,
    FunctionalOverlap,
    MatchType,
    OwnershipAlignment,
    PartialMatchSubtype,
    ProductionContextDifference,
    RequirementComparison,
    ScopeAlignment,
)


class CandidateComparisonStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    PARTIAL = "PARTIAL"
    INSUFFICIENT_CANDIDATE_EVIDENCE = "INSUFFICIENT_CANDIDATE_EVIDENCE"
    INSUFFICIENT_MARKET_REQUIREMENTS = "INSUFFICIENT_MARKET_REQUIREMENTS"
    INSUFFICIENT_ANALYSIS = "INSUFFICIENT_ANALYSIS"
    FAILED = "FAILED"


class TransferabilityAssessment(BaseModel):
    """Strict reasoning-model output for one requirement and bounded evidence set."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    requirement_id: UUID
    match_type: MatchType
    supporting_evidence_ids: list[UUID] = Field(default_factory=list)
    functional_overlap: FunctionalOverlap
    ownership_alignment: OwnershipAlignment
    scope_alignment: ScopeAlignment
    production_context_difference: ProductionContextDifference
    partial_match_subtype: PartialMatchSubtype | None = None
    transferable_capability: str | None = None
    remaining_difference: str = Field(min_length=1, max_length=500)
    confidence: ConfidenceLevel
    explanation: str = Field(min_length=1, max_length=800)

    @model_validator(mode="after")
    def validate_semantic_match(self) -> "TransferabilityAssessment":
        if self.match_type is MatchType.DIRECT_MATCH:
            raise ValueError("direct matches must be determined without the reasoning model")
        if self.match_type in {MatchType.TRANSFERABLE_MATCH, MatchType.PARTIAL_MATCH}:
            if not self.supporting_evidence_ids:
                raise ValueError("supported semantic matches require evidence references")
        if self.match_type is MatchType.PARTIAL_MATCH and self.partial_match_subtype is None:
            raise ValueError("partial matches require a calibrated subtype")
        if (
            self.match_type is not MatchType.PARTIAL_MATCH
            and self.partial_match_subtype is not None
        ):
            raise ValueError("only partial matches may carry a partial subtype")
        if self.match_type is MatchType.NO_CONFIRMED_MATCH and self.supporting_evidence_ids:
            raise ValueError("no-confirmed-match cannot cite supporting evidence")
        return self


class CandidateComparisonResult(BaseModel):
    """Run-level comparison output without an aggregate fit score."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: CandidateComparisonStatus
    comparisons: list[RequirementComparison] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    deterministic_count: int = Field(default=0, ge=0)
    semantic_count: int = Field(default=0, ge=0)
    failed_count: int = Field(default=0, ge=0)
