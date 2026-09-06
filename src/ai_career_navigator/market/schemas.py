"""Project-owned schemas for bounded current-market retrieval."""

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from ai_career_navigator.domain import (
    ConfidenceLevel,
    CurrentMarketSnapshot,
    GeographyScope,
    GoalType,
    JobPosting,
    SourceRecord,
)


class SearchScope(StrEnum):
    EXACT = "EXACT"
    RELATED = "RELATED"


class MarketSourceProvider(StrEnum):
    ADZUNA = "ADZUNA"
    YOU = "YOU"


class PostingSourceType(StrEnum):
    STRUCTURED_JOB = "STRUCTURED_JOB"
    DIRECT_ATS_POSTING = "DIRECT_ATS_POSTING"
    DIRECT_EMPLOYER_POSTING = "DIRECT_EMPLOYER_POSTING"
    AGGREGATOR_PAGE = "AGGREGATOR_PAGE"
    BACKGROUND_CONTEXT = "BACKGROUND_CONTEXT"


class RetrievalQuality(StrEnum):
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"


class PostingSeniority(StrEnum):
    ASSOCIATE_JUNIOR = "ASSOCIATE_JUNIOR"
    STANDARD = "STANDARD"
    SENIOR = "SENIOR"
    STAFF_LEAD = "STAFF_LEAD"
    UNKNOWN = "UNKNOWN"


class SourceAgreement(StrEnum):
    CROSS_SOURCE_CONFIRMED = "CROSS_SOURCE_CONFIRMED"
    SINGLE_SOURCE_SUPPORTED = "SINGLE_SOURCE_SUPPORTED"
    LOW_SUPPORT = "LOW_SUPPORT"


class EnrichmentStatus(StrEnum):
    NOT_NEEDED = "NOT_NEEDED"
    NOT_ATTEMPTED = "NOT_ATTEMPTED"
    APPLIED = "APPLIED"
    FAILED = "FAILED"
    CONFLICT_REJECTED = "CONFLICT_REJECTED"


class SearchPassType(StrEnum):
    DIRECT_SOURCE = "DIRECT_SOURCE"
    GENERAL_WEB = "GENERAL_WEB"
    TARGET_VARIANT = "TARGET_VARIANT"
    RELATED_TITLE = "RELATED_TITLE"
    ATS_PRIMARY = "ATS_PRIMARY"
    ATS_FALLBACK = "ATS_FALLBACK"


class SearchFreshness(StrEnum):
    MONTH = "month"
    YEAR = "year"


class SearchPlanStatus(StrEnum):
    READY = "READY"
    SEARCH_PLAN_REQUIRES_ROLE_DISCOVERY = "SEARCH_PLAN_REQUIRES_ROLE_DISCOVERY"


class GeographyQueryVariant(BaseModel):
    """One deterministic geography phrase and its two exact-title query forms."""

    model_config = ConfigDict(frozen=True)

    scope: GeographyScope
    location_phrase: str = Field(min_length=1)
    direct_source_query: str = Field(min_length=1)
    general_query: str = Field(min_length=1)


class SearchPlan(BaseModel):
    """Serializable deterministic instructions for one V1 market run."""

    model_config = ConfigDict(frozen=True)

    status: SearchPlanStatus
    goal_type: GoalType
    target_role: str | None = None
    search_title: str | None = None
    target_seniority: str | None = None
    geography: str
    preferred_work_modes: list[str] = Field(default_factory=list)
    target_industries: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    expansion_permitted: bool = False
    target_title_variants: list[str] = Field(default_factory=list)
    allowed_geography_scopes: list[GeographyScope] = Field(default_factory=list)
    geography_queries: list[GeographyQueryVariant] = Field(default_factory=list)
    direct_source_queries: list[str] = Field(default_factory=list)
    exact_queries: list[str] = Field(default_factory=list)


class SearchLimits(BaseModel):
    """Configuration-controlled bounds for one market retrieval."""

    model_config = ConfigDict(frozen=True)

    max_search_queries: int = Field(default=3, ge=1, le=10)
    max_variant_queries: int = Field(default=4, ge=0, le=10)
    max_expansion_queries: int = Field(default=3, ge=0, le=10)
    max_content_fetches: int = Field(default=30, ge=1, le=100)
    target_posting_count: int = Field(default=20, ge=1, le=100)
    expansion_threshold: int = Field(default=8, ge=1, le=100)
    max_retries: int = Field(default=2, ge=0, le=5)
    discovery_result_count: int = Field(default=12, ge=10, le=15)
    thin_description_characters: int = Field(default=500, ge=100, le=5000)
    max_you_candidate_results: int = Field(default=10, ge=1, le=10)
    you_fallback_threshold: int = Field(default=3, ge=1, le=10)
    direct_source_excluded_domains: list[str] = Field(
        default_factory=lambda: [
            "ziprecruiter.com",
            "indeed.com",
            "glassdoor.com",
            "glassdoor.ca",
            "linkedin.com",
            "jobilize.com",
        ]
    )


class MarketSearchRequest(BaseModel):
    """Provider-neutral parameters for one observable discovery pass."""

    model_config = ConfigDict(frozen=True)

    query: str = Field(min_length=1)
    pass_type: SearchPassType
    freshness: SearchFreshness
    count: int = Field(default=12, ge=10, le=15)
    country: str = Field(default="CA", min_length=2, max_length=2)
    language: str = Field(default="EN", min_length=2, max_length=2)
    excluded_domains: list[str] = Field(default_factory=list)
    geography_scope: GeographyScope = GeographyScope.STRICT_CITY


class SearchPassReport(BaseModel):
    """Safe, explainable outcome for one staged market-search call."""

    model_config = ConfigDict(frozen=True)

    pass_type: SearchPassType
    freshness: SearchFreshness
    query: str
    raw_result_count: int = Field(ge=0)
    validated_posting_count: int = Field(ge=0)
    aggregator_result_count: int = Field(ge=0)
    direct_page_count: int = Field(ge=0)
    geography_scope: GeographyScope
    geography_valid_posting_count: int = Field(ge=0)


class MarketSearchResult(BaseModel):
    """A provider-independent candidate result, not yet a job posting."""

    model_config = ConfigDict(frozen=True)

    title: str = Field(min_length=1)
    url: str = Field(min_length=1)
    snippets: list[str] = Field(default_factory=list)
    source_domain: str | None = None

    @field_validator("title", "url", "source_domain", mode="before")
    @classmethod
    def strip_optional_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class StructuredJobSearchRequest(BaseModel):
    """Provider-neutral request for a page of structured job advertisements."""

    model_config = ConfigDict(frozen=True)

    title: str = Field(min_length=1)
    location: str = Field(min_length=1)
    page: int = Field(default=1, ge=1, le=20)
    results_per_page: int = Field(default=12, ge=1, le=50)
    country: str = Field(default="ca", pattern=r"^[a-z]{2}$")
    pass_type: SearchPassType = SearchPassType.DIRECT_SOURCE
    geography_scope: GeographyScope = GeographyScope.COUNTRY


class StructuredJobResult(BaseModel):
    """One normalized structured posting returned by a primary provider."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: MarketSourceProvider
    provider_job_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    url: str = Field(min_length=1)
    description: str = ""
    company: str | None = None
    location: str | None = None
    created: date | None = None
    category: str | None = None
    contract_type: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None


class StructuredJobSearchPage(BaseModel):
    """Normalized bounded page with provider-reported discovery metadata."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: MarketSourceProvider
    page: int = Field(ge=1)
    total_available: int | None = Field(default=None, ge=0)
    results: list[StructuredJobResult] = Field(default_factory=list)
    malformed_result_count: int = Field(default=0, ge=0)


class MarketPageContent(BaseModel):
    """Cleaned untrusted page data returned by the integration boundary."""

    model_config = ConfigDict(frozen=True)

    url: str = Field(min_length=1)
    title: str | None = None
    markdown: str = ""
    employer: str | None = None
    location: str | None = None
    work_mode: str | None = None
    employment_type: str | None = None
    seniority: str | None = None
    posting_date: str | None = None
    closing_date: str | None = None
    active_status: str | None = None


class RetainedSourceContent(BaseModel):
    """One retained source paired with its untrusted retrieved content."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source: SourceRecord
    content: MarketPageContent


class MarketPostingEvidence(BaseModel):
    """Service-level provenance chain for one retained posting."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    posting: JobPosting
    primary_source: SourceRecord
    primary_content: MarketPageContent
    supporting_sources: list[SourceRecord] = Field(default_factory=list)
    supporting_contents: list[MarketPageContent] = Field(default_factory=list)
    enrichment_status: EnrichmentStatus = EnrichmentStatus.NOT_NEEDED
    provider_sources: list[MarketSourceProvider] = Field(default_factory=list)
    source_type: PostingSourceType = PostingSourceType.STRUCTURED_JOB
    retrieval_quality: RetrievalQuality = RetrievalQuality.MODERATE
    title_classification: str | None = None
    seniority_classification: PostingSeniority = PostingSeniority.UNKNOWN
    selected_content_source: MarketSourceProvider | None = None
    limitations: list[str] = Field(default_factory=list)


class PostingRetrievalAudit(BaseModel):
    """Bounded discovery-to-selection facts without retaining full posting content."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    posting_id: str | None = None
    provider: MarketSourceProvider
    source_url: str = Field(min_length=1)
    source_type: PostingSourceType
    title: str = Field(min_length=1)
    employer: str | None = None
    location: str | None = None
    title_classification: str | None = None
    seniority_classification: PostingSeniority = PostingSeniority.UNKNOWN
    duplicate_of: str | None = None
    selected_content_source: MarketSourceProvider | None = None
    selected_for_primary_evidence: bool = False
    rejection_reason: str | None = None


class MarketRetrievalResult(BaseModel):
    """Complete service result without provider objects or session handles."""

    model_config = ConfigDict(frozen=True)

    plan: SearchPlan
    snapshot: CurrentMarketSnapshot | None = None
    sources: list[SourceRecord] = Field(default_factory=list)
    source_contents: list[RetainedSourceContent] = Field(default_factory=list)
    postings: list[JobPosting] = Field(default_factory=list)
    rejected_result_count: int = Field(default=0, ge=0)
    exact_search_queries: list[str] = Field(default_factory=list)
    exact_raw_result_count: int = Field(default=0, ge=0)
    exact_title_validated_count: int = Field(default=0, ge=0)
    target_variant_search_queries: list[str] = Field(default_factory=list)
    target_variant_raw_result_count: int = Field(default=0, ge=0)
    target_variant_validated_count: int = Field(default=0, ge=0)
    expansion_triggered: bool = False
    expansion_titles: list[str] = Field(default_factory=list)
    related_search_queries: list[str] = Field(default_factory=list)
    related_raw_result_count: int = Field(default=0, ge=0)
    related_title_validated_count: int = Field(default=0, ge=0)
    geography_out_of_scope_count: int = Field(default=0, ge=0)
    geography_unclear_count: int = Field(default=0, ge=0)
    raw_source_count: int = Field(default=0, ge=0)
    segmented_candidate_count: int = Field(default=0, ge=0)
    title_grounded_candidate_count: int = Field(default=0, ge=0)
    geography_valid_candidate_count: int = Field(default=0, ge=0)
    rejected_url_like_title_count: int = Field(default=0, ge=0)
    total_unique_retained_posting_count: int = Field(default=0, ge=0)
    search_passes: list[SearchPassReport] = Field(default_factory=list)
    freshness_fallback_used: bool = False
    aggregator_result_count: int = Field(default=0, ge=0)
    direct_page_count: int = Field(default=0, ge=0)
    geography_valid_postings_by_scope: dict[GeographyScope, int] = Field(default_factory=dict)
    posting_evidence: list[MarketPostingEvidence] = Field(default_factory=list)
    primary_provider: MarketSourceProvider | None = None
    enrichment_provider: MarketSourceProvider | None = None
    degraded_discovery: bool = False
    primary_search_count: int = Field(default=0, ge=0)
    enrichment_attempt_count: int = Field(default=0, ge=0)
    enrichment_success_count: int = Field(default=0, ge=0)
    parallel_discovery: bool = False
    you_search_count: int = Field(default=0, ge=0)
    adzuna_raw_result_count: int = Field(default=0, ge=0)
    adzuna_validated_count: int = Field(default=0, ge=0)
    you_validated_count: int = Field(default=0, ge=0)
    cross_source_match_count: int = Field(default=0, ge=0)
    source_coverage_confidence: ConfidenceLevel = ConfidenceLevel.INSUFFICIENT
    source_coverage_reason: str | None = None
    posting_audits: list[PostingRetrievalAudit] = Field(default_factory=list)
    you_raw_result_count: int = Field(default=0, ge=0)
    you_direct_posting_count: int = Field(default=0, ge=0)
    you_context_result_count: int = Field(default=0, ge=0)
    you_rejected_result_count: int = Field(default=0, ge=0)
    you_fallback_triggered: bool = False

    @property
    def requires_role_discovery(self) -> bool:
        return self.plan.status is SearchPlanStatus.SEARCH_PLAN_REQUIRES_ROLE_DISCOVERY


class MarketProviderSummary(BaseModel):
    """Checkpoint-safe provider and enrichment facts for transparent UI rendering."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    primary_provider: MarketSourceProvider | None = None
    enrichment_provider: MarketSourceProvider | None = None
    degraded_discovery: bool = False
    primary_search_count: int = Field(default=0, ge=0)
    enrichment_attempt_count: int = Field(default=0, ge=0)
    enrichment_success_count: int = Field(default=0, ge=0)
    parallel_discovery: bool = False
    you_search_count: int = Field(default=0, ge=0)
    adzuna_raw_result_count: int = Field(default=0, ge=0)
    adzuna_validated_count: int = Field(default=0, ge=0)
    you_validated_count: int = Field(default=0, ge=0)
    cross_source_match_count: int = Field(default=0, ge=0)
    source_coverage_confidence: ConfidenceLevel = ConfidenceLevel.INSUFFICIENT
    source_coverage_reason: str | None = None
    you_raw_result_count: int = Field(default=0, ge=0)
    you_direct_posting_count: int = Field(default=0, ge=0)
    you_context_result_count: int = Field(default=0, ge=0)
    you_rejected_result_count: int = Field(default=0, ge=0)
    you_fallback_triggered: bool = False


class ValidatedUrl(BaseModel):
    """Internal helper that validates a candidate URL without retaining provider data."""

    url: HttpUrl
