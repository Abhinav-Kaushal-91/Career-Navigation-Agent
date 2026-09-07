"""Current-market evidence and derived snapshot schemas for V1."""

from datetime import UTC, date, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl, model_validator

from ai_career_navigator.domain.enums import (
    ConfidenceLevel,
    EmployerDiversity,
    EvidenceMaturity,
    GeographyScope,
    MarketConcentration,
    OpportunityAvailability,
    RequirementCategory,
    RequirementStatementType,
)


def _now_utc() -> datetime:
    return datetime.now(UTC)


class SourceRecord(BaseModel):
    """Minimal retained metadata for an external V1 source."""

    model_config = ConfigDict(frozen=True)

    source_id: UUID = Field(default_factory=uuid4)
    source_type: str = Field(min_length=1)
    title: str = Field(min_length=1)
    url: HttpUrl
    employer: str | None = None
    geography: str | None = None
    retrieval_date: date
    publication_date: date | None = None
    accessible: bool = True
    limitations: list[str] = Field(default_factory=list)


class JobPosting(BaseModel):
    """A current job posting as observed from one retained source."""

    model_config = ConfigDict(frozen=True)

    posting_id: UUID = Field(default_factory=uuid4)
    source_id: UUID
    original_title: str = Field(min_length=1)
    normalized_title: str | None = None
    role_family: str | None = None
    employer: str | None = None
    location: str | None = None
    location_evidence_text: str | None = Field(default=None, max_length=500)
    requested_geography_scope: GeographyScope | None = None
    matched_geography_scope: GeographyScope | None = None
    grounded_location: str | None = None
    work_mode: str | None = None
    employment_type: str | None = None
    seniority: str | None = None
    posting_date: date | None = None
    closing_date: date | None = None
    retrieved_at: AwareDatetime = Field(default_factory=_now_utc)
    active_status: str | None = None
    requisition_id: str | None = None
    canonical_job_url: str | None = None
    content_fingerprint: str | None = None
    discovered_at: AwareDatetime | None = None
    currentness_checked_at: AwareDatetime | None = None
    currentness_basis: str = "UNKNOWN"
    title_match_kind: str | None = None
    duplicate_group_id: UUID | None = None
    extraction_confidence: ConfidenceLevel

    @model_validator(mode="after")
    def validate_posting_dates(self) -> "JobPosting":
        if self.posting_date and self.closing_date and self.closing_date < self.posting_date:
            raise ValueError("closing_date must not precede posting_date")
        return self


class RoleRequirement(BaseModel):
    """A structured requirement derived from a validated posting."""

    model_config = ConfigDict(frozen=True)

    requirement_id: UUID = Field(default_factory=uuid4)
    posting_id: UUID
    category: RequirementCategory
    statement_type: RequirementStatementType = RequirementStatementType.HIRING_CAPABILITY
    requirement_text: str = Field(min_length=1)
    normalized_capability: str | None = None
    source_section: str | None = None
    qualifier_quotes: list[str] = Field(default_factory=list)
    relationship: Literal["SINGLE", "ANY_OF"] = "SINGLE"
    capability_options: list[str] = Field(default_factory=list)
    mandatory: bool = False
    preferred: bool = False
    employer_specific: bool = False
    years_required: float | None = Field(default=None, ge=0)
    maturity_expected: EvidenceMaturity | None = None
    frequency_within_sample: float | None = Field(default=None, ge=0, le=1)
    extraction_confidence: ConfidenceLevel

    @model_validator(mode="after")
    def validate_requirement_flags(self) -> "RoleRequirement":
        if self.mandatory and self.preferred:
            raise ValueError("a requirement cannot be both mandatory and preferred")
        return self


class CurrentMarketSnapshot(BaseModel):
    """A bounded V1 summary of validated current-market evidence."""

    model_config = ConfigDict(frozen=True)

    snapshot_id: UUID = Field(default_factory=uuid4)
    target_role: str = Field(min_length=1)
    geography: str = Field(min_length=1)
    search_date: date
    exact_title_count: int = Field(ge=0)
    target_variant_count: int = Field(default=0, ge=0)
    related_title_count: int = Field(ge=0)
    validated_posting_count: int = Field(ge=0)
    distinct_employer_count: int = Field(ge=0)
    related_titles: list[str] = Field(default_factory=list)
    target_variant_titles: list[str] = Field(default_factory=list)
    common_requirements: list[UUID] = Field(default_factory=list)
    opportunity_availability: OpportunityAvailability
    employer_diversity: EmployerDiversity
    market_concentration: MarketConcentration
    evidence_confidence: ConfidenceLevel
    source_ids: list[UUID] = Field(default_factory=list)
    employer_posting_counts: dict[str, int] = Field(default_factory=dict)
    location_posting_counts: dict[str, int] = Field(default_factory=dict)
    known_employer_posting_count: int = Field(default=0, ge=0)
    largest_employer_posting_count: int = Field(default=0, ge=0)
    top_three_employer_posting_count: int = Field(default=0, ge=0)
    search_query_count: int = Field(default=0, ge=0)
    successful_search_query_count: int = Field(default=0, ge=0)
    content_fetch_count: int = Field(default=0, ge=0)
    successful_content_fetch_count: int = Field(default=0, ge=0)
    duplicate_posting_count: int = Field(default=0, ge=0)
    limitations: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_explainability_counts(self) -> "CurrentMarketSnapshot":
        if (
            self.exact_title_count + self.target_variant_count + self.related_title_count
            != self.validated_posting_count
        ):
            raise ValueError(
                "exact, target-variant, and related counts must equal validated postings"
            )
        if any(count <= 0 for count in self.employer_posting_counts.values()):
            raise ValueError("employer posting counts must be positive")
        if any(count <= 0 for count in self.location_posting_counts.values()):
            raise ValueError("location posting counts must be positive")
        if sum(self.location_posting_counts.values()) > self.validated_posting_count:
            raise ValueError("known location count cannot exceed validated postings")
        if self.distinct_employer_count != len(self.employer_posting_counts):
            raise ValueError("distinct_employer_count must match employer_posting_counts")
        if sum(self.employer_posting_counts.values()) != self.known_employer_posting_count:
            raise ValueError("known employer count must match employer_posting_counts")
        ordered_counts = sorted(self.employer_posting_counts.values(), reverse=True)
        expected_largest = ordered_counts[0] if ordered_counts else 0
        expected_top_three = sum(ordered_counts[:3])
        if self.largest_employer_posting_count != expected_largest:
            raise ValueError("largest employer count must match employer_posting_counts")
        if self.top_three_employer_posting_count != expected_top_three:
            raise ValueError("top-three employer count must match employer_posting_counts")
        if self.known_employer_posting_count > self.validated_posting_count:
            raise ValueError("known employer count cannot exceed validated postings")
        if self.successful_search_query_count > self.search_query_count:
            raise ValueError("successful search count cannot exceed attempted searches")
        if self.successful_content_fetch_count > self.content_fetch_count:
            raise ValueError("successful content count cannot exceed attempted fetches")
        return self
