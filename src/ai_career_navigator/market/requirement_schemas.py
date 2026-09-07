"""Provider-neutral schemas for posting segmentation and market requirements."""

from datetime import date
from enum import StrEnum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from ai_career_navigator.domain import (
    ConfidenceLevel,
    EvidenceMaturity,
    GeographyScope,
    JobPosting,
    RequirementCategory,
    RequirementFrequency,
    RequirementStatementType,
    RoleRequirement,
)
from ai_career_navigator.market.schemas import MarketSourceProvider, SourceAgreement


class SourceContentType(StrEnum):
    DIRECT_JOB_PAGE = "DIRECT_JOB_PAGE"
    AGGREGATOR_JOB_PAGE = "AGGREGATOR_JOB_PAGE"
    MIXED_JOB_CONTENT = "MIXED_JOB_CONTENT"
    INSUFFICIENT_JOB_CONTENT = "INSUFFICIENT_JOB_CONTENT"


class PostingGeographyStatus(StrEnum):
    IN_SCOPE = "IN_SCOPE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    UNCLEAR = "UNCLEAR"


class PostingTitleMatch(StrEnum):
    EXACT_TARGET = "EXACT_TARGET"
    TARGET_VARIANT = "TARGET_VARIANT"
    RELATED_TITLE = "RELATED_TITLE"
    IRRELEVANT = "IRRELEVANT"


class RequirementRunStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    PARTIAL = "PARTIAL"
    EMPTY = "EMPTY"
    FAILED = "FAILED"


class RoleProfileStatus(StrEnum):
    STABLE = "STABLE"
    PROVISIONAL = "PROVISIONAL"
    INSUFFICIENT = "INSUFFICIENT"


class CanonicalRequirementScope(StrEnum):
    CORE = "CORE"
    SECONDARY = "SECONDARY"
    OPTIONAL = "OPTIONAL"
    PREREQUISITE = "PREREQUISITE"


class CanonicalRequirementKind(StrEnum):
    CAPABILITY = "CAPABILITY"
    EXPERIENCE_THRESHOLD = "EXPERIENCE_THRESHOLD"
    PREREQUISITE = "PREREQUISITE"
    ROLE_RESPONSIBILITY = "ROLE_RESPONSIBILITY"
    PREFERENCE = "PREFERENCE"


class RequirementAuditStatus(StrEnum):
    GROUNDING_FAILED = "GROUNDING_FAILED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class TargetVariantClassification(StrEnum):
    VALID_TARGET_VARIANT = "VALID_TARGET_VARIANT"
    RELATED_TITLE = "RELATED_TITLE"
    REJECTED = "REJECTED"


class SeniorityAlignment(StrEnum):
    ALIGNED = "ALIGNED"
    UNCERTAIN = "UNCERTAIN"
    MISALIGNED = "MISALIGNED"


class RequirementItemType(StrEnum):
    ROLE_RESPONSIBILITY = "ROLE_RESPONSIBILITY"
    HIRING_CAPABILITY = "HIRING_CAPABILITY"
    PREREQUISITE = "PREREQUISITE"
    PREFERENCE = "PREFERENCE"
    METADATA_NON_REQUIREMENT = "METADATA_NON_REQUIREMENT"


class PostingCandidate(BaseModel):
    """A posting-specific, source-grounded unit segmented from one source."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    candidate_id: UUID = Field(default_factory=uuid4)
    posting_id: UUID = Field(default_factory=uuid4)
    source_id: UUID
    source_reference: str = Field(min_length=1)
    provider: str | None = None
    provider_sources: list[str] = Field(default_factory=list)
    source_type: str | None = None
    source_url: str | None = None
    source_provenance: list[str] = Field(default_factory=list)
    retrieval_quality: str | None = None
    seniority_classification: str | None = None
    selected_content_source: str | None = None
    title_classification: str | None = None
    posting_date: date | None = None
    requisition_id: str | None = None
    canonical_job_url: str | None = None
    content_fingerprint: str | None = None
    source_reference_text: str = Field(min_length=1, max_length=2000)
    title: str = Field(min_length=1)
    employer: str | None = None
    location: str | None = None
    location_evidence_text: str | None = Field(default=None, max_length=500)
    posting_text: str = Field(min_length=1, max_length=20_000)
    extraction_confidence: ConfidenceLevel

    @field_validator(
        "source_reference",
        "source_reference_text",
        "source_url",
        "title",
        "employer",
        "location",
        "location_evidence_text",
        "posting_text",
        mode="before",
    )
    @classmethod
    def clean_text(cls, value: object) -> object:
        if isinstance(value, str):
            return " ".join(value.split())
        return value


class PostingCandidateAssessment(BaseModel):
    """Deterministic title and geography decisions for one candidate."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    candidate: PostingCandidate
    geography_status: PostingGeographyStatus
    geography_evidence_text: str | None = Field(default=None, max_length=500)
    requested_geography_scope: GeographyScope | None = None
    matched_geography_scope: GeographyScope | None = None
    title_match: PostingTitleMatch


class SourceProcessingResult(BaseModel):
    """Classification and segmented candidates for one retained source."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: UUID
    content_type: SourceContentType
    candidates: list[PostingCandidate] = Field(default_factory=list)
    segmented_candidate_count: int = Field(default=0, ge=0)
    title_grounded_candidate_count: int = Field(default=0, ge=0)
    rejected_url_like_title_count: int = Field(default=0, ge=0)
    rejected_search_heading_title_count: int = Field(default=0, ge=0)
    aggregator_reported_count: int | None = Field(default=None, ge=0)
    limitations: list[str] = Field(default_factory=list)


class ModelPostingCandidate(BaseModel):
    """Strict extraction-model output used only when deterministic segmentation fails."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str = Field(min_length=1)
    employer: str | None = None
    location: str | None = None
    source_reference_text: str = Field(min_length=1, max_length=2000)
    posting_text: str = Field(min_length=1, max_length=20_000)


class ModelSegmentationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    candidates: list[ModelPostingCandidate] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class ExtractedRequirement(BaseModel):
    """One source-quoted requirement returned by the extraction model."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_quote: str = Field(min_length=1, max_length=2000)
    category: RequirementCategory
    normalized_capability: str | None = None
    source_section: str | None = Field(default=None, max_length=160)
    qualifier_quotes: list[str] = Field(default_factory=list, max_length=8)
    relationship: Literal["SINGLE", "ANY_OF"] = "SINGLE"
    capability_options: list[str] = Field(default_factory=list, max_length=8)
    mandatory: bool = False
    preferred: bool = False
    years_required: float | None = Field(default=None, ge=0)
    maturity_expected: EvidenceMaturity | None = None
    confidence: ConfidenceLevel
    item_type: RequirementItemType = RequirementItemType.HIRING_CAPABILITY

    @model_validator(mode="after")
    def validate_flags(self) -> "ExtractedRequirement":
        if self.mandatory and self.preferred:
            raise ValueError("a requirement cannot be both mandatory and preferred")
        if self.relationship == "ANY_OF" and len(self.capability_options) < 2:
            raise ValueError("ANY_OF needs at least two source-supported alternatives")
        return self


class PostingRequirementResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    requirements: list[ExtractedRequirement] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class PostingExtractionQuality(BaseModel):
    """Safe per-posting QA counters; no full posting content is retained."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    posting_id: UUID
    source_id: UUID
    title: str
    employer: str | None = None
    input_description_characters: int = Field(ge=0)
    enrichment_used: bool = False
    schema_valid_response: bool | None = None
    raw_extracted_item_count: int = Field(ge=0)
    accepted_capability_requirement_count: int = Field(ge=0)
    accepted_role_responsibility_count: int = Field(default=0, ge=0)
    accepted_preference_count: int = Field(default=0, ge=0)
    prerequisite_condition_count: int = Field(ge=0)
    rejected_metadata_non_requirement_count: int = Field(ge=0)
    unsupported_grounding_count: int = Field(default=0, ge=0)
    failure_category: str | None = None
    limitations: list[str] = Field(default_factory=list)


class PostingRequirementAuditItem(BaseModel):
    """Bounded requirement-level provenance without retaining a complete posting body."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_requirement_id: UUID | None = None
    source_quote: str = Field(min_length=1, max_length=2000)
    normalized_capability: str | None = Field(default=None, max_length=120)
    category: RequirementCategory
    item_type: RequirementItemType
    accepted: bool
    final_classification: str = Field(min_length=1, max_length=120)
    rejection_or_override_reason: str | None = Field(default=None, max_length=500)
    canonical_requirement_id: UUID | None = None


class PostingRequirementAudit(BaseModel):
    """Posting-level trace from extraction through canonical-role consolidation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    posting_id: UUID
    title: str = Field(min_length=1)
    employer: str | None = None
    location: str | None = None
    title_classification: PostingTitleMatch
    provider: str | None = None
    source_reference: str = Field(min_length=1)
    extraction_status: RequirementAuditStatus
    items: list[PostingRequirementAuditItem] = Field(default_factory=list)


class TargetVariantAssessment(BaseModel):
    """Strict model output for one observed title; it cannot create evidence."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    candidate_title: str = Field(min_length=1, max_length=180)
    classification: TargetVariantClassification
    functional_overlap: float = Field(ge=0, le=1)
    ownership_overlap: float = Field(ge=0, le=1)
    scope_overlap: float = Field(ge=0, le=1)
    seniority_alignment: SeniorityAlignment
    outcome_overlap: float = Field(ge=0, le=1)
    core_requirement_overlap: float | None = Field(default=None, ge=0, le=1)
    evidence_confidence: ConfidenceLevel
    supporting_posting_ids: list[UUID] = Field(default_factory=list)
    reasoning_summary: str = Field(min_length=1, max_length=500)


class TargetVariantAssessmentResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    assessments: list[TargetVariantAssessment] = Field(min_length=1, max_length=5)

    @model_validator(mode="before")
    @classmethod
    def remove_redundant_nemotron_schema_flag(cls, value: object) -> object:
        """Discard one observed provider echo without relaxing the output contract."""

        if not isinstance(value, dict) or value.get("target_variant_assessment_result") is not True:
            return value
        normalized = dict(value)
        normalized.pop("target_variant_assessment_result")
        return normalized


class TargetVariantAudit(BaseModel):
    """Validated promotion decision for one observed related title."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    candidate_title: str = Field(min_length=1, max_length=180)
    source_posting_ids: list[UUID] = Field(min_length=1, max_length=10)
    original_classification: PostingTitleMatch
    validated_classification: PostingTitleMatch
    seniority_alignment: SeniorityAlignment
    functional_overlap: float | None = Field(default=None, ge=0, le=1)
    ownership_overlap: float | None = Field(default=None, ge=0, le=1)
    scope_overlap: float | None = Field(default=None, ge=0, le=1)
    outcome_overlap: float | None = Field(default=None, ge=0, le=1)
    core_requirement_overlap: float | None = Field(default=None, ge=0, le=1)
    confidence: ConfidenceLevel
    reason: str = Field(min_length=1, max_length=500)
    promoted: bool = False


class AggregatedRequirement(BaseModel):
    """Exact-title and combined frequency for one normalized requirement."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    category: RequirementCategory
    normalized_capability: str = Field(min_length=1)
    requirement_ids: list[UUID] = Field(default_factory=list)
    exact_title_occurrence_count: int = Field(ge=0)
    target_variant_occurrence_count: int = Field(default=0, ge=0)
    related_title_occurrence_count: int = Field(ge=0)
    exact_title_frequency: float | None = Field(default=None, ge=0, le=1)
    exact_and_variant_frequency: float | None = Field(default=None, ge=0, le=1)
    combined_frequency: float = Field(ge=0, le=1)


class CanonicalRoleRequirement(BaseModel):
    """One deduplicated target-role expectation with source-level provenance."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    canonical_requirement_id: UUID = Field(default_factory=uuid4)
    display_name: str = Field(min_length=1, max_length=120)
    category: RequirementCategory
    requirement_kind: CanonicalRequirementKind
    expected_maturity: EvidenceMaturity | None = None
    maturity_support_counts: dict[str, int] = Field(default_factory=dict)
    years_required: float | None = Field(default=None, ge=0)
    years_required_by_source: dict[str, float] = Field(default_factory=dict)
    baseline_requirement_ids: list[UUID] | None = None
    baseline_posting_ids: list[UUID] = Field(default_factory=list)
    qualifier_notes: list[str] = Field(default_factory=list)
    source_section: str | None = None
    qualifier_quotes: list[str] = Field(default_factory=list)
    relationship: Literal["SINGLE", "ANY_OF"] = "SINGLE"
    capability_options: list[str] = Field(default_factory=list)
    mandatory_signal: bool = False
    preferred_signal: bool = False
    employer_specific: bool = False
    frequency_band: RequirementFrequency
    primary_support_ratio: float = Field(ge=0, le=1)
    employer_support_count: int = Field(ge=0)
    exact_employer_support_count: int = Field(default=0, ge=0)
    variant_employer_support_count: int = Field(default=0, ge=0)
    posting_support_count: int = Field(ge=0)
    responsibility_support_count: int = Field(default=0, ge=0)
    qualification_support_count: int = Field(default=0, ge=0)
    exact_support_count: int = Field(ge=0)
    variant_support_count: int = Field(ge=0)
    related_support_count: int = Field(ge=0)
    adzuna_support_count: int = Field(default=0, ge=0)
    you_support_count: int = Field(default=0, ge=0)
    source_agreement: SourceAgreement = SourceAgreement.LOW_SUPPORT
    supporting_requirement_ids: list[UUID] = Field(min_length=1)
    responsibility_requirement_ids: list[UUID] = Field(default_factory=list)
    qualification_requirement_ids: list[UUID] = Field(default_factory=list)
    supporting_posting_ids: list[UUID] = Field(min_length=1)
    supporting_employers: list[str] = Field(default_factory=list)
    provider_sources: list[MarketSourceProvider] = Field(default_factory=list)
    source_provenance: list[str] = Field(default_factory=list)
    statement_types: list[RequirementStatementType] = Field(default_factory=list)
    representative_source_quotes: list[str] = Field(min_length=1, max_length=3)
    confidence: ConfidenceLevel
    requirement_scope: CanonicalRequirementScope

    @property
    def comparison_requirement_ids(self) -> list[UUID]:
        """Return only source statements permitted to support candidate comparison."""

        if self.baseline_requirement_ids is not None:
            return self.baseline_requirement_ids
        return self.qualification_requirement_ids or self.supporting_requirement_ids

    def as_role_requirement(self) -> RoleRequirement:
        """Project the canonical object into the existing comparison contract."""

        return RoleRequirement(
            requirement_id=self.canonical_requirement_id,
            posting_id=(self.baseline_posting_ids or self.supporting_posting_ids)[0],
            category=self.category,
            statement_type=RequirementStatementType.HIRING_CAPABILITY,
            requirement_text=self.representative_source_quotes[0],
            normalized_capability=self.display_name,
            source_section=self.source_section,
            qualifier_quotes=self.qualifier_quotes,
            relationship=self.relationship,
            capability_options=self.capability_options,
            mandatory=self.mandatory_signal,
            preferred=self.preferred_signal,
            employer_specific=self.employer_specific,
            years_required=self.years_required,
            maturity_expected=self.expected_maturity,
            frequency_within_sample=self.primary_support_ratio,
            extraction_confidence=self.confidence,
        )


class CanonicalTargetRoleProfile(BaseModel):
    """Evidence-grounded target-role representation for one bounded market sample."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    target_role: str = Field(min_length=1)
    geography: str = Field(min_length=1)
    profile_status: RoleProfileStatus
    confidence: ConfidenceLevel
    exact_posting_count: int = Field(ge=0)
    variant_posting_count: int = Field(ge=0)
    related_posting_count: int = Field(ge=0)
    distinct_exact_employer_count: int = Field(ge=0)
    distinct_variant_employer_count: int = Field(default=0, ge=0)
    analyzed_exact_posting_count: int = Field(ge=0)
    analyzed_variant_posting_count: int = Field(ge=0)
    analyzed_related_posting_count: int = Field(ge=0)
    generated_at: AwareDatetime
    requirements: list[CanonicalRoleRequirement] = Field(default_factory=list)
    responsibilities: list[CanonicalRoleRequirement] = Field(default_factory=list)
    prerequisites: list[CanonicalRoleRequirement] = Field(default_factory=list)
    preferences: list[CanonicalRoleRequirement] = Field(default_factory=list)
    optional_signals: list[CanonicalRoleRequirement] = Field(default_factory=list)
    related_context: list[CanonicalRoleRequirement] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)

    @property
    def comparison_requirements(self) -> tuple[CanonicalRoleRequirement, ...]:
        if self.profile_status is RoleProfileStatus.INSUFFICIENT:
            return ()
        return tuple(
            item
            for item in [*self.requirements, *self.prerequisites]
            if item.requirement_scope
            in {
                CanonicalRequirementScope.CORE,
                CanonicalRequirementScope.SECONDARY,
                CanonicalRequirementScope.PREREQUISITE,
            }
        )


class MarketRequirementSummary(BaseModel):
    """Explainable requirement frequencies over successfully analyzed postings."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    target_role: str = Field(min_length=1)
    geography: str = Field(min_length=1)
    source_page_count: int = Field(ge=0)
    identified_candidate_count: int = Field(ge=0)
    validated_in_scope_posting_count: int = Field(ge=0)
    analyzed_posting_count: int = Field(ge=0)
    schema_valid_extraction_count: int | None = Field(default=None, ge=0)
    postings_with_accepted_hiring_requirements: int = Field(default=0, ge=0)
    postings_with_accepted_role_responsibilities: int = Field(default=0, ge=0)
    rejected_grounding_item_count: int = Field(default=0, ge=0)
    exact_title_analyzed_count: int = Field(ge=0)
    target_variant_analyzed_count: int = Field(default=0, ge=0)
    related_title_analyzed_count: int = Field(ge=0)
    out_of_scope_count: int = Field(ge=0)
    unclear_geography_count: int = Field(ge=0)
    irrelevant_title_count: int = Field(ge=0)
    requirements: list[AggregatedRequirement] = Field(default_factory=list)
    capability_requirements: list[AggregatedRequirement] = Field(default_factory=list)
    prerequisite_requirements: list[AggregatedRequirement] = Field(default_factory=list)
    posting_quality: list[PostingExtractionQuality] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_denominators(self) -> "MarketRequirementSummary":
        if (
            self.exact_title_analyzed_count
            + self.target_variant_analyzed_count
            + self.related_title_analyzed_count
            != self.analyzed_posting_count
        ):
            raise ValueError(
                "exact, target-variant, and related counts must equal analyzed postings"
            )
        if self.analyzed_posting_count > self.validated_in_scope_posting_count:
            raise ValueError("analyzed postings cannot exceed validated in-scope postings")
        if self.schema_valid_extraction_count is not None:
            if (
                not self.analyzed_posting_count
                <= self.schema_valid_extraction_count
                <= self.validated_in_scope_posting_count
            ):
                raise ValueError(
                    "schema-valid responses must cover analyzed postings within selected inputs"
                )
            if (
                max(
                    self.postings_with_accepted_hiring_requirements,
                    self.postings_with_accepted_role_responsibilities,
                )
                > self.schema_valid_extraction_count
            ):
                raise ValueError("grounded evidence posting count exceeds schema-valid responses")
        return self


class MarketRequirementAnalysis(BaseModel):
    """Complete provider-independent result of Activity 5B processing."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: RequirementRunStatus
    source_results: list[SourceProcessingResult] = Field(default_factory=list)
    assessments: list[PostingCandidateAssessment] = Field(default_factory=list)
    postings: list[JobPosting] = Field(default_factory=list)
    requirements: list[RoleRequirement] = Field(default_factory=list)
    raw_requirements: list[RoleRequirement] = Field(default_factory=list)
    canonical_profile: CanonicalTargetRoleProfile | None = None
    initial_canonical_profile: CanonicalTargetRoleProfile | None = None
    posting_audits: list[PostingRequirementAudit] = Field(default_factory=list)
    target_variant_audits: list[TargetVariantAudit] = Field(default_factory=list)
    target_variant_expansion_attempted: bool = False
    summary: MarketRequirementSummary
