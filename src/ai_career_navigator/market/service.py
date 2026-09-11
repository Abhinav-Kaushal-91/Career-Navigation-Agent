"""Provider-independent current-market evidence retrieval service."""

import asyncio
import logging
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from time import perf_counter

from ai_career_navigator.config import Settings
from ai_career_navigator.domain import (
    CareerGoal,
    CurrentMarketSnapshot,
    GeographyScope,
    JobPosting,
    SourceRecord,
)
from ai_career_navigator.market.currentness import currentness_rejection
from ai_career_navigator.market.deduplication import (
    deduplicate_postings,
    deduplicate_search_results,
)
from ai_career_navigator.market.errors import (
    MarketAuthenticationError,
    MarketConfigurationError,
    MarketIntelligenceError,
)
from ai_career_navigator.market.mcp.protocol import MarketSearchClient
from ai_career_navigator.market.normalization import (
    canonicalize_url,
    create_job_posting,
    create_source_record,
    normalize_employer,
    normalize_whitespace,
    source_domain,
)
from ai_career_navigator.market.processing import (
    assess_candidate,
    assess_title,
    classify_and_segment_source,
    classify_seniority,
)
from ai_career_navigator.market.requirement_schemas import (
    PostingGeographyStatus,
    PostingTitleMatch,
    SourceContentType,
)
from ai_career_navigator.market.schemas import (
    MarketRetrievalResult,
    MarketSearchRequest,
    MarketSearchResult,
    MarketSourceProvider,
    PostingRetrievalAudit,
    PostingSourceType,
    RetainedSourceContent,
    SearchFreshness,
    SearchLimits,
    SearchPassReport,
    SearchPassType,
    SearchPlan,
    SearchPlanStatus,
)
from ai_career_navigator.market.search_plan import (
    build_related_query,
    build_search_plan,
    build_you_ats_query,
    build_you_query_family,
)
from ai_career_navigator.market.signals import (
    SignalInputs,
    classify_concentration,
    classify_employer_diversity,
    classify_evidence_confidence,
    classify_opportunity,
    concentration_counts,
)
from ai_career_navigator.market.source_registry import (
    is_ats_domain,
    is_individual_job_board_url,
    looks_like_individual_job_url,
)
from ai_career_navigator.market.validation import (
    is_promising_search_result,
    observed_related_titles,
    title_equivalence_reason,
)

logger = logging.getLogger(__name__)


def _is_ats_domain(domain: str | None) -> bool:
    return is_ats_domain(domain)


def _looks_like_employer_posting_url(url: str) -> bool:
    return looks_like_individual_job_url(url)


def _geography_scope_allowed(
    matched_scope: GeographyScope | None,
    plan: SearchPlan,
) -> bool:
    if matched_scope in plan.allowed_geography_scopes:
        return True
    if (
        matched_scope is GeographyScope.COUNTRY_REMOTE
        and GeographyScope.COUNTRY in plan.allowed_geography_scopes
    ):
        work_modes = {item.casefold() for item in plan.preferred_work_modes}
        return not work_modes or bool({"remote", "flexible / no preference"} & work_modes)
    return False


@dataclass
class _RunMetrics:
    search_attempts: int = 0
    search_successes: int = 0
    content_attempts: int = 0
    content_successes: int = 0
    rejected_results: int = 0
    rejected_candidates: int = 0
    budget_deferred_results: int = 0
    discovered_urls: set[str] = field(default_factory=set)
    structured_content_attempts: int = 0
    structured_content_successes: int = 0
    duplicate_count: int = 0
    malformed_response_count: int = 0
    content_failure_count: int = 0
    exact_raw_result_count: int = 0
    target_variant_raw_result_count: int = 0
    related_raw_result_count: int = 0
    geography_out_of_scope_count: int = 0
    geography_unclear_count: int = 0
    segmented_candidate_count: int = 0
    title_grounded_candidate_count: int = 0
    geography_valid_candidate_count: int = 0
    geography_valid_postings_by_scope: Counter[GeographyScope] = field(default_factory=Counter)
    rejected_url_like_title_count: int = 0
    aggregator_result_count: int = 0
    direct_page_count: int = 0
    exact_search_queries: list[str] = field(default_factory=list)
    target_variant_search_queries: list[str] = field(default_factory=list)
    related_search_queries: list[str] = field(default_factory=list)
    expansion_triggered: bool = False
    expansion_titles: list[str] = field(default_factory=list)
    observed_related_posting_titles: list[str] = field(default_factory=list)
    search_passes: list[SearchPassReport] = field(default_factory=list)
    freshness_fallback_used: bool = False
    limitations: list[str] = field(default_factory=list)
    posting_audits: list[PostingRetrievalAudit] = field(default_factory=list)


def limits_from_settings(settings: Settings) -> SearchLimits:
    return SearchLimits(
        max_search_queries=settings.market_max_search_queries,
        max_expansion_queries=settings.market_max_expansion_queries,
        max_content_fetches=settings.market_max_content_fetches,
        analysis_posting_limit=settings.market_analysis_posting_limit,
        max_enrichments=settings.market_max_enrichments,
        target_posting_count=settings.market_target_posting_count,
        expansion_threshold=settings.market_expansion_threshold,
        max_retries=settings.max_retries,
        discovery_result_count=settings.market_discovery_result_count,
        thin_description_characters=settings.market_thin_description_characters,
        direct_source_excluded_domains=settings.market_direct_excluded_domains,
        max_posting_age_days=settings.market_max_posting_age_days,
        max_total_search_calls=settings.market_max_total_search_calls,
    )


async def _retry_call(  # type: ignore[no-untyped-def]
    operation, *, max_retries: int, operation_name: str
):
    retry_count = 0
    while True:
        try:
            return await operation()
        except MarketIntelligenceError as error:
            if not error.retryable or retry_count >= max_retries:
                raise
            retry_count += 1
            logger.warning(
                "market_operation_retry operation=%s retry_count=%d category=%s",
                operation_name,
                retry_count,
                type(error).__name__,
            )
            await asyncio.sleep(min(0.1 * (2 ** (retry_count - 1)), 0.5))


async def _search(
    client: MarketSearchClient,
    request: MarketSearchRequest,
    metrics: _RunMetrics,
    limits: SearchLimits,
) -> list[MarketSearchResult]:
    metrics.search_attempts += 1
    try:
        results = await _retry_call(
            lambda: client.search(request),
            max_retries=limits.max_retries,
            operation_name="search",
        )
    except MarketIntelligenceError as error:
        metrics.search_passes.append(
            SearchPassReport(
                provider=MarketSourceProvider.YOU,
                request_parameters=request.model_dump(mode="json"),
                succeeded=False,
                failure_category=type(error).__name__,
                pass_type=request.pass_type,
                freshness=request.freshness,
                query=request.query,
                raw_result_count=0,
                validated_posting_count=0,
                aggregator_result_count=0,
                direct_page_count=0,
                geography_scope=request.geography_scope,
                geography_valid_posting_count=0,
            )
        )
        raise
    metrics.search_successes += 1
    metrics.discovered_urls.update(
        url for result in results if (url := canonicalize_url(result.url))
    )
    return results


async def _retrieve_candidates(
    *,
    client: MarketSearchClient,
    candidates: list[MarketSearchResult],
    plan: SearchPlan,
    limits: SearchLimits,
    metrics: _RunMetrics,
    seen_urls: set[str],
    sources: list[SourceRecord],
    source_contents: list[RetainedSourceContent],
    postings: list[JobPosting],
    retrieval_date: date,
    retrieved_at: datetime,
    excluded_domains: list[str] | None = None,
    included_domains: list[str] | None = None,
    requested_geography_scope: GeographyScope = GeographyScope.STRICT_CITY,
    content_attempt_cap: int | None = None,
    provider: MarketSourceProvider | None = None,
    individual_postings_only: bool = False,
    candidate_result_cap: int | None = None,
) -> None:
    target = plan.search_title or plan.target_role or ""
    exclusions = {domain.casefold().removeprefix("www.") for domain in excluded_domains or []}
    inclusions = {domain.casefold().removeprefix("www.") for domain in included_domains or []}

    def domain_allowed(item: MarketSearchResult) -> bool:
        # Recheck provider filters against the actual URL before spending a content call.
        domain = (source_domain(item.url) or "").casefold().removeprefix("www.")

        def matches(candidate: str) -> bool:
            return domain == candidate or domain.endswith(f".{candidate}")

        return not any(matches(value) for value in exclusions) and (
            not inclusions or any(matches(value) for value in inclusions)
        )

    allowed = [item for item in candidates if domain_allowed(item)]
    metrics.rejected_results += len(candidates) - len(allowed)
    if provider is not None:
        allowed_urls = {item.url for item in allowed}
        metrics.posting_audits.extend(
            PostingRetrievalAudit(
                provider=provider,
                source_url=item.url,
                source_type=PostingSourceType.AGGREGATOR_PAGE,
                title=item.title,
                rejection_reason="Outside requested discovery domain policy.",
            )
            for item in candidates
            if item.url not in allowed_urls
        )
    promising = [item for item in allowed if is_promising_search_result(item, target)]
    metrics.rejected_results += len(allowed) - len(promising)
    if provider is not None:
        promising_urls = {item.url for item in promising}
        metrics.posting_audits.extend(
            PostingRetrievalAudit(
                provider=provider,
                source_url=item.url,
                source_type=PostingSourceType.BACKGROUND_CONTEXT,
                title=item.title,
                rejection_reason="Generic or non-posting page was retained as context only.",
            )
            for item in allowed
            if item.url not in promising_urls
        )
    unique, url_duplicates = deduplicate_search_results(promising)
    metrics.duplicate_count += url_duplicates

    attempt_cap = content_attempt_cap or limits.max_content_fetches

    def primary_count() -> int:
        return sum(
            posting.title_match_kind
            in {
                "LITERAL_EXACT",
                "LEXICAL_EQUIVALENCE",
                "DESCRIPTIVE_SUFFIX_GROUNDED",
                "DESCRIPTION_SUPPORTED_SPECIALTY",
                "TARGET_VARIANT",
            }
            for posting in deduplicate_postings(postings)[0]
        )

    for candidate_index, candidate in enumerate(unique[:candidate_result_cap]):
        if primary_count() >= limits.target_posting_count:
            metrics.budget_deferred_results += len(unique) - candidate_index
            break
        if metrics.content_attempts >= attempt_cap:
            metrics.budget_deferred_results += len(unique) - candidate_index
            metrics.limitations.append(
                f"Content retrieval was capped at {attempt_cap} source pages for this stage."
            )
            break
        canonical = canonicalize_url(candidate.url)
        if canonical is None:
            metrics.rejected_results += 1
            continue
        if canonical in seen_urls:
            metrics.duplicate_count += 1
            continue
        seen_urls.add(canonical)
        metrics.content_attempts += 1
        try:
            page = await _retry_call(
                lambda candidate_url=candidate.url: client.fetch_content(candidate_url),
                max_retries=limits.max_retries,
                operation_name="fetch_content",
            )
            metrics.content_successes += 1
        except (MarketAuthenticationError, MarketConfigurationError):
            raise
        except MarketIntelligenceError as error:
            metrics.content_failure_count += 1
            metrics.posting_audits.append(
                PostingRetrievalAudit(
                    provider=provider or MarketSourceProvider.YOU,
                    source_url=candidate.url,
                    title=candidate.title,
                    source_type=PostingSourceType.BACKGROUND_CONTEXT,
                    stage="CONTENT_FETCH",
                    decision_unit="SEARCH_RESULT",
                    parent_result_id=canonical,
                    rejection_reason=f"Content fetch failed: {type(error).__name__}.",
                )
            )
            logger.warning("market_content_failed category=%s", type(error).__name__)
            sources.append(
                create_source_record(
                    candidate,
                    retrieval_date=retrieval_date,
                    accessible=False,
                    limitations=["Source page could not be retrieved."],
                )
            )
            continue

        currentness_error = currentness_rejection(
            page, as_of=retrieval_date, max_age_days=limits.max_posting_age_days
        )
        if currentness_error:
            if currentness_error.startswith("Invalid posting dates"):
                metrics.malformed_response_count += 1
            metrics.rejected_results += 1
            metrics.posting_audits.append(
                PostingRetrievalAudit(
                    provider=provider or MarketSourceProvider.YOU,
                    source_url=candidate.url,
                    title=candidate.title,
                    source_type=PostingSourceType.DIRECT_ATS_POSTING
                    if _is_ats_domain(source_domain(candidate.url))
                    else PostingSourceType.DIRECT_EMPLOYER_POSTING,
                    stage="CURRENTNESS",
                    decision_unit="SEARCH_RESULT",
                    parent_result_id=canonical,
                    rejection_reason=currentness_error,
                )
            )
            continue

        try:
            source = create_source_record(candidate, retrieval_date=retrieval_date, page=page)
            if provider is not None:
                source = source.model_copy(update={"source_type": provider.value})
        except ValueError:
            metrics.malformed_response_count += 1
            metrics.rejected_results += 1
            logger.warning("market_candidate_rejected category=SCHEMA_VALIDATION_ERROR")
            continue
        sources.append(source)
        retained = RetainedSourceContent(source=source, content=page)
        source_contents.append(retained)
        processed = classify_and_segment_source(retained)
        domain = candidate.source_domain or source_domain(candidate.url)
        source_type = (
            PostingSourceType.INDIVIDUAL_JOB_BOARD_POSTING
            if is_individual_job_board_url(candidate.url)
            and processed.content_type is SourceContentType.DIRECT_JOB_PAGE
            else PostingSourceType.DIRECT_ATS_POSTING
            if _is_ats_domain(domain)
            and processed.content_type is SourceContentType.DIRECT_JOB_PAGE
            else PostingSourceType.DIRECT_EMPLOYER_POSTING
            if processed.content_type is SourceContentType.DIRECT_JOB_PAGE
            and _looks_like_employer_posting_url(candidate.url)
            else PostingSourceType.AGGREGATOR_PAGE
            if processed.candidates
            else PostingSourceType.BACKGROUND_CONTEXT
        )
        if individual_postings_only and source_type not in {
            PostingSourceType.INDIVIDUAL_JOB_BOARD_POSTING,
            PostingSourceType.DIRECT_ATS_POSTING,
            PostingSourceType.DIRECT_EMPLOYER_POSTING,
        }:
            metrics.rejected_results += 1
            metrics.rejected_candidates += len(processed.candidates)
            metrics.posting_audits.append(
                PostingRetrievalAudit(
                    provider=provider or MarketSourceProvider.YOU,
                    source_url=candidate.url,
                    source_type=source_type,
                    title=candidate.title,
                    selected_for_primary_evidence=False,
                    rejection_reason="Context-only source; not an individual job posting.",
                )
            )
            continue
        if processed.content_type is SourceContentType.DIRECT_JOB_PAGE:
            metrics.direct_page_count += 1
        metrics.segmented_candidate_count += processed.segmented_candidate_count
        metrics.title_grounded_candidate_count += processed.title_grounded_candidate_count
        metrics.rejected_url_like_title_count += processed.rejected_url_like_title_count
        assessments = [
            assess_candidate(
                item,
                target_role=target,
                target_geography=plan.geography,
                requested_geography_scope=requested_geography_scope,
                target_seniority=plan.target_seniority,
            )
            for item in processed.candidates
        ]
        geography_valid = [
            item
            for item in assessments
            if item.geography_status is PostingGeographyStatus.IN_SCOPE
            and _geography_scope_allowed(item.matched_geography_scope, plan)
        ]
        metrics.geography_valid_candidate_count += len(geography_valid)
        metrics.geography_valid_postings_by_scope.update(
            item.matched_geography_scope
            for item in geography_valid
            if item.matched_geography_scope is not None
        )
        metrics.observed_related_posting_titles.extend(
            item.candidate.title
            for item in assessments
            if item.title_match is PostingTitleMatch.RELATED_TITLE
        )
        metrics.geography_out_of_scope_count += sum(
            item.geography_status is PostingGeographyStatus.OUT_OF_SCOPE
            or (
                item.geography_status is PostingGeographyStatus.IN_SCOPE
                and not _geography_scope_allowed(item.matched_geography_scope, plan)
            )
            for item in assessments
        )
        metrics.geography_unclear_count += sum(
            item.geography_status is PostingGeographyStatus.UNCLEAR for item in assessments
        )
        eligible = [
            item
            for item in assessments
            if item in geography_valid and item.title_match is not PostingTitleMatch.IRRELEVANT
        ]
        metrics.rejected_candidates += len(assessments) - len(eligible)
        for assessment in assessments:
            if assessment not in eligible:
                metrics.posting_audits.append(
                    PostingRetrievalAudit(
                        provider=provider or MarketSourceProvider.YOU,
                        source_url=candidate.url,
                        title=assessment.candidate.title,
                        posting_id=str(assessment.candidate.posting_id),
                        source_type=source_type,
                        parent_result_id=canonical,
                        decision_unit="POSTING_CANDIDATE",
                        rejection_reason=(
                            "Title is irrelevant to the target."
                            if assessment.title_match is PostingTitleMatch.IRRELEVANT
                            else f"Geography validation: {assessment.geography_status.value}; "
                            "allowed scope check failed."
                        ),
                    )
                )
        if not eligible:
            metrics.rejected_results += 1
            continue
        for assessment in eligible:
            posting_candidate = assessment.candidate
            segmented_result = candidate.model_copy(update={"title": posting_candidate.title})
            segmented_page = page.model_copy(
                update={
                    "title": posting_candidate.title,
                    "employer": posting_candidate.employer,
                    "location": posting_candidate.location,
                    "markdown": posting_candidate.posting_text,
                }
            )
            try:
                posting = create_job_posting(
                    segmented_result,
                    segmented_page,
                    source,
                    retrieved_at=retrieved_at,
                ).model_copy(
                    update={
                        "posting_id": posting_candidate.posting_id,
                        "location_evidence_text": posting_candidate.location_evidence_text,
                        "requested_geography_scope": assessment.requested_geography_scope,
                        "matched_geography_scope": assessment.matched_geography_scope,
                        "grounded_location": posting_candidate.location,
                        "extraction_confidence": posting_candidate.extraction_confidence,
                        "canonical_job_url": (
                            canonicalize_url(page.canonical_job_url or page.url)
                            if source_type
                            in {
                                PostingSourceType.INDIVIDUAL_JOB_BOARD_POSTING,
                                PostingSourceType.DIRECT_ATS_POSTING,
                                PostingSourceType.DIRECT_EMPLOYER_POSTING,
                            }
                            else None
                        ),
                        "requisition_id": page.requisition_id
                        if len(processed.candidates) == 1
                        else None,
                        "title_match_kind": title_equivalence_reason(
                            posting_candidate.title, target, posting_candidate.posting_text
                        )
                        or (
                            "TARGET_VARIANT"
                            if assessment.title_match is PostingTitleMatch.TARGET_VARIANT
                            else assessment.title_match.value
                        ),
                    }
                )
            except ValueError:
                metrics.malformed_response_count += 1
                metrics.rejected_candidates += 1
                continue
            postings.append(posting)
            title_classification = assessment.title_match.value
            seniority = classify_seniority(posting_candidate.title)
            metrics.posting_audits.append(
                PostingRetrievalAudit(
                    posting_id=str(posting.posting_id),
                    provider=provider or MarketSourceProvider.YOU,
                    source_url=candidate.url,
                    source_type=source_type,
                    title=posting.original_title,
                    employer=posting.employer,
                    location=posting.grounded_location or posting.location,
                    title_classification=title_classification,
                    seniority_classification=seniority,
                    selected_content_source=provider or MarketSourceProvider.YOU,
                    selected_for_primary_evidence=True,
                    title_match_kind=posting.title_match_kind,
                    parent_result_id=canonical,
                )
            )


def _employer_counts(postings: list[JobPosting]) -> dict[str, int]:
    names: dict[str, str] = {}
    counts: Counter[str] = Counter()
    for posting in postings:
        employer = normalize_employer(posting.employer)
        if employer:
            key = employer.casefold()
            names.setdefault(key, employer)
            counts[key] += 1
    return {names[key]: counts[key] for key in sorted(counts)}


def _location_counts(postings: list[JobPosting]) -> dict[str, int]:
    names: dict[str, str] = {}
    counts: Counter[str] = Counter()
    for posting in postings:
        location = normalize_whitespace(posting.grounded_location or posting.location or "")
        if location:
            key = location.casefold()
            names.setdefault(key, location)
            counts[key] += 1
    return {
        names[key]: counts[key]
        for key in sorted(counts, key=lambda item: (-counts[item], names[item].casefold()))
    }


def _snapshot(
    *,
    plan: SearchPlan,
    postings: list[JobPosting],
    sources: list[SourceRecord],
    metrics: _RunMetrics,
    search_date: date,
) -> CurrentMarketSnapshot:
    unique_postings, posting_duplicates = deduplicate_postings(postings)
    metrics.duplicate_count += posting_duplicates
    postings[:] = unique_postings
    employer_counts = _employer_counts(postings)
    location_counts = _location_counts(postings)
    title_matches = {
        posting.posting_id: PostingTitleMatch.TARGET_VARIANT
        if posting.title_match_kind
        in {
            "LEXICAL_EQUIVALENCE",
            "DESCRIPTIVE_SUFFIX_GROUNDED",
            "TARGET_VARIANT",
            "DESCRIPTION_SUPPORTED_SPECIALTY",
        }
        else assess_title(
            posting.original_title,
            plan.search_title or "",
        )
        for posting in postings
    }
    exact = [
        posting
        for posting in postings
        if title_matches[posting.posting_id] is PostingTitleMatch.EXACT_TARGET
    ]
    target_variants = [
        posting
        for posting in postings
        if title_matches[posting.posting_id] is PostingTitleMatch.TARGET_VARIANT
    ]
    related = [
        posting
        for posting in postings
        if title_matches[posting.posting_id] is PostingTitleMatch.RELATED_TITLE
    ]
    related_titles = sorted(
        {posting.normalized_title or posting.original_title for posting in related},
        key=str.casefold,
    )
    inputs = SignalInputs(
        validated_postings=len(postings),
        employer_counts=employer_counts,
        search_attempts=metrics.search_attempts,
        search_successes=metrics.search_successes,
        content_attempts=metrics.content_attempts + metrics.structured_content_attempts,
        content_successes=metrics.content_successes + metrics.structured_content_successes,
        duplicate_count=metrics.duplicate_count,
        malformed_response_count=metrics.malformed_response_count,
    )
    known, largest, top_three = concentration_counts(inputs)
    limitations = list(dict.fromkeys(metrics.limitations))
    if metrics.content_failure_count:
        limitations.append(f"{metrics.content_failure_count} source pages could not be retrieved.")
    if known < len(postings):
        limitations.append(
            f"Employer was unavailable for {len(postings) - known} validated postings."
        )
    if not postings:
        limitations.append(
            "Too little validated current evidence was found to classify the market."
        )
    validated_source_ids = {posting.source_id for posting in postings}
    return CurrentMarketSnapshot(
        target_role=plan.target_role or "",
        geography=plan.geography,
        search_date=search_date,
        exact_title_count=len(exact),
        target_variant_count=len(target_variants),
        related_title_count=len(related),
        validated_posting_count=len(postings),
        distinct_employer_count=len(employer_counts),
        related_titles=related_titles,
        target_variant_titles=sorted(
            {posting.normalized_title or posting.original_title for posting in target_variants},
            key=str.casefold,
        ),
        opportunity_availability=classify_opportunity(inputs),
        employer_diversity=classify_employer_diversity(inputs),
        market_concentration=classify_concentration(inputs),
        evidence_confidence=classify_evidence_confidence(inputs),
        source_ids=[
            source.source_id for source in sources if source.source_id in validated_source_ids
        ],
        employer_posting_counts=employer_counts,
        location_posting_counts=location_counts,
        known_employer_posting_count=known,
        largest_employer_posting_count=largest,
        top_three_employer_posting_count=top_three,
        search_query_count=metrics.search_attempts,
        successful_search_query_count=metrics.search_successes,
        content_fetch_count=metrics.content_attempts,
        successful_content_fetch_count=metrics.content_successes,
        duplicate_posting_count=metrics.duplicate_count,
        limitations=limitations,
    )


async def _retrieve_you_ats_market(
    *,
    goal: CareerGoal,
    client: MarketSearchClient,
    plan: SearchPlan,
    limits: SearchLimits,
    timestamp: datetime,
) -> MarketRetrievalResult:
    """Run one ATS-focused You.com pass and at most one bounded fallback."""

    metrics = _RunMetrics()
    sources: list[SourceRecord] = []
    source_contents: list[RetainedSourceContent] = []
    postings: list[JobPosting] = []
    seen_urls: set[str] = set()
    scope = plan.allowed_geography_scopes[0]

    async def run(request: MarketSearchRequest) -> None:
        query, pass_type = request.query, request.pass_type
        before = len(postings)
        results = await _search(
            client,
            request,
            metrics,
            limits,
        )
        bounded_results = results[: limits.max_you_candidate_results]
        metrics.budget_deferred_results += max(0, len(results) - len(bounded_results))
        metrics.exact_search_queries.append(query)
        metrics.exact_raw_result_count += len(results)
        await _retrieve_candidates(
            client=client,
            candidates=bounded_results,
            plan=plan,
            limits=limits,
            metrics=metrics,
            seen_urls=seen_urls,
            sources=sources,
            source_contents=source_contents,
            postings=postings,
            retrieval_date=timestamp.date(),
            retrieved_at=timestamp,
            requested_geography_scope=scope,
            provider=MarketSourceProvider.YOU,
            individual_postings_only=True,
            excluded_domains=request.excluded_domains,
            included_domains=request.included_domains,
            candidate_result_cap=limits.max_you_candidate_results,
        )
        metrics.search_passes.append(
            SearchPassReport(
                provider=MarketSourceProvider.YOU,
                request_parameters=request.model_dump(mode="json"),
                pass_type=pass_type,
                freshness=request.freshness,
                query=query,
                raw_result_count=len(results),
                validated_posting_count=max(0, len(postings) - before),
                aggregator_result_count=sum(
                    audit.source_type is PostingSourceType.AGGREGATOR_PAGE
                    for audit in metrics.posting_audits
                    if audit.source_url in {item.url for item in bounded_results}
                ),
                direct_page_count=max(0, len(postings) - before),
                geography_scope=scope,
                geography_valid_posting_count=max(0, len(postings) - before),
            )
        )

    async with client:
        for index, request in enumerate(
            build_you_query_family(plan)[
                : min(limits.max_search_queries, limits.max_total_search_calls)
            ]
        ):
            if (
                index > 1
                and sum(
                    item.title_match_kind
                    in {
                        "LITERAL_EXACT",
                        "LEXICAL_EQUIVALENCE",
                        "DESCRIPTIVE_SUFFIX_GROUNDED",
                        "DESCRIPTION_SUPPORTED_SPECIALTY",
                        "TARGET_VARIANT",
                    }
                    for item in deduplicate_postings(postings)[0]
                )
                >= limits.you_fallback_threshold
            ):
                break
            if metrics.content_attempts >= limits.max_content_fetches:
                break
            metrics.freshness_fallback_used |= index > 0
            try:
                await run(request)
            except MarketIntelligenceError as error:
                metrics.limitations.append(f"You.com query failed: {type(error).__name__}.")
                if isinstance(error, (MarketAuthenticationError, MarketConfigurationError)):
                    raise

    snapshot = _snapshot(
        plan=plan,
        postings=postings,
        sources=sources,
        metrics=metrics,
        search_date=timestamp.date(),
    )
    context_count = sum(
        audit.source_type
        in {PostingSourceType.AGGREGATOR_PAGE, PostingSourceType.BACKGROUND_CONTEXT}
        for audit in metrics.posting_audits
    )
    return MarketRetrievalResult(
        plan=plan,
        snapshot=snapshot,
        sources=sources,
        source_contents=source_contents,
        postings=postings,
        posting_audits=metrics.posting_audits,
        rejected_result_count=metrics.rejected_results,
        exact_search_queries=metrics.exact_search_queries,
        exact_raw_result_count=metrics.exact_raw_result_count,
        exact_title_validated_count=snapshot.exact_title_count,
        target_variant_validated_count=snapshot.target_variant_count,
        related_title_validated_count=snapshot.related_title_count,
        geography_out_of_scope_count=metrics.geography_out_of_scope_count,
        geography_unclear_count=metrics.geography_unclear_count,
        raw_source_count=metrics.content_successes,
        segmented_candidate_count=metrics.segmented_candidate_count,
        title_grounded_candidate_count=metrics.title_grounded_candidate_count,
        geography_valid_candidate_count=metrics.geography_valid_candidate_count,
        rejected_url_like_title_count=metrics.rejected_url_like_title_count,
        total_unique_retained_posting_count=snapshot.validated_posting_count,
        search_passes=metrics.search_passes,
        freshness_fallback_used=metrics.freshness_fallback_used,
        aggregator_result_count=context_count,
        direct_page_count=len(postings),
        primary_provider=MarketSourceProvider.YOU,
        you_search_count=metrics.search_attempts,
        you_raw_result_count=metrics.exact_raw_result_count,
        you_direct_posting_count=len(postings),
        you_context_result_count=context_count,
        you_rejected_result_count=metrics.rejected_results,
        you_fallback_triggered=metrics.freshness_fallback_used,
        rejected_candidate_count=metrics.rejected_candidates,
        fetch_failure_count=metrics.content_failure_count,
        unique_url_count=len(metrics.discovered_urls),
        budget_deferred_result_count=metrics.budget_deferred_results,
        effective_budgets={
            "search_calls": min(3, limits.max_search_queries),
            "content_fetches": limits.max_content_fetches,
            "max_posting_age_days": limits.max_posting_age_days,
        },
    )


async def retrieve_current_market(
    goal: CareerGoal,
    client: MarketSearchClient,
    *,
    limits: SearchLimits | None = None,
    now: datetime | None = None,
    ats_primary: bool = False,
) -> MarketRetrievalResult:
    """Retrieve current evidence without evaluating candidate qualifications."""

    plan = build_search_plan(goal)
    if plan.status is SearchPlanStatus.SEARCH_PLAN_REQUIRES_ROLE_DISCOVERY:
        return MarketRetrievalResult(plan=plan)

    bounded = limits or SearchLimits()
    timestamp = now or datetime.now(UTC)
    if ats_primary:
        return await _retrieve_you_ats_market(
            goal=goal,
            client=client,
            plan=plan,
            limits=bounded,
            timestamp=timestamp,
        )
    metrics = _RunMetrics()
    sources: list[SourceRecord] = []
    source_contents: list[RetainedSourceContent] = []
    postings: list[JobPosting] = []
    observed_result_count = 0
    seen_urls: set[str] = set()
    started = perf_counter()
    logger.info("market_search_started exact_query_count=%d", len(plan.exact_queries))

    def unique_posting_count() -> int:
        return len(deduplicate_postings(postings)[0])

    def target_evidence_count() -> int:
        return sum(
            item.title_match_kind == "DESCRIPTION_SUPPORTED_SPECIALTY"
            or assess_title(
                item.normalized_title or item.original_title,
                plan.search_title or "",
            )
            in {PostingTitleMatch.EXACT_TARGET, PostingTitleMatch.TARGET_VARIANT}
            for item in deduplicate_postings(postings)[0]
        )

    def aggregator_count(results: list[MarketSearchResult]) -> int:
        excluded = {
            domain.casefold().removeprefix("www.")
            for domain in bounded.direct_source_excluded_domains
        }
        count = 0
        for result in results:
            domain = (result.source_domain or source_domain(result.url) or "").casefold()
            if any(domain == item or domain.endswith(f".{item}") for item in excluded):
                count += 1
        return count

    async def run_pass(
        request: MarketSearchRequest,
        *,
        content_attempt_cap: int | None = None,
    ) -> None:
        nonlocal observed_result_count
        if metrics.search_attempts >= bounded.max_total_search_calls:
            metrics.limitations.append("Shared search-query budget was exhausted.")
            return
        before_postings = unique_posting_count()
        before_direct_pages = metrics.direct_page_count
        results = await _search(client, request, metrics, bounded)
        observed_result_count += len(results)
        aggregators = aggregator_count(results)
        metrics.aggregator_result_count += aggregators
        if request.pass_type is SearchPassType.RELATED_TITLE:
            metrics.related_search_queries.append(request.query)
            metrics.related_raw_result_count += len(results)
        elif request.pass_type is SearchPassType.TARGET_VARIANT:
            metrics.target_variant_search_queries.append(request.query)
            metrics.target_variant_raw_result_count += len(results)
        else:
            metrics.exact_search_queries.append(request.query)
            metrics.exact_raw_result_count += len(results)
        await _retrieve_candidates(
            client=client,
            candidates=results,
            plan=plan,
            limits=bounded,
            metrics=metrics,
            seen_urls=seen_urls,
            sources=sources,
            source_contents=source_contents,
            postings=postings,
            retrieval_date=timestamp.date(),
            retrieved_at=timestamp,
            excluded_domains=request.excluded_domains or None,
            requested_geography_scope=request.geography_scope,
            content_attempt_cap=content_attempt_cap,
        )
        metrics.search_passes.append(
            SearchPassReport(
                provider=MarketSourceProvider.YOU,
                request_parameters=request.model_dump(mode="json"),
                pass_type=request.pass_type,
                freshness=request.freshness,
                query=request.query,
                raw_result_count=len(results),
                validated_posting_count=max(0, unique_posting_count() - before_postings),
                aggregator_result_count=aggregators,
                direct_page_count=metrics.direct_page_count - before_direct_pages,
                geography_scope=request.geography_scope,
                geography_valid_posting_count=max(0, unique_posting_count() - before_postings),
            )
        )

    def request(
        query: str,
        pass_type: SearchPassType,
        freshness: SearchFreshness,
        geography_scope: GeographyScope,
    ) -> MarketSearchRequest:
        return MarketSearchRequest(
            query=query,
            pass_type=pass_type,
            freshness=freshness,
            count=bounded.discovery_result_count,
            country="CA",
            language="EN",
            excluded_domains=(
                bounded.direct_source_excluded_domains
                if pass_type in {SearchPassType.DIRECT_SOURCE, SearchPassType.TARGET_VARIANT}
                else []
            ),
            geography_scope=geography_scope,
        )

    def needs_more_for_qa() -> bool:
        return (
            target_evidence_count() < 3
            and metrics.content_attempts < bounded.max_content_fetches
            and metrics.search_attempts < bounded.max_total_search_calls
        )

    async with client:
        variants = plan.geography_queries[: bounded.max_search_queries]
        variant_reserve = min(
            6,
            max(0, bounded.max_content_fetches - 6),
        )
        exact_content_cap = bounded.max_content_fetches - variant_reserve
        for variant in variants:
            await run_pass(
                request(
                    variant.direct_source_query,
                    SearchPassType.DIRECT_SOURCE,
                    SearchFreshness.MONTH,
                    variant.scope,
                ),
                content_attempt_cap=exact_content_cap,
            )
            if not needs_more_for_qa():
                break
        if needs_more_for_qa():
            for variant in variants:
                await run_pass(
                    request(
                        variant.general_query,
                        SearchPassType.GENERAL_WEB,
                        SearchFreshness.MONTH,
                        variant.scope,
                    ),
                    content_attempt_cap=exact_content_cap,
                )
                if not needs_more_for_qa():
                    break

        if needs_more_for_qa():
            metrics.freshness_fallback_used = True
            for variant in variants:
                await run_pass(
                    request(
                        variant.direct_source_query,
                        SearchPassType.DIRECT_SOURCE,
                        SearchFreshness.YEAR,
                        variant.scope,
                    ),
                    content_attempt_cap=exact_content_cap,
                )
                if not needs_more_for_qa():
                    break
            if needs_more_for_qa():
                for variant in variants:
                    await run_pass(
                        request(
                            variant.general_query,
                            SearchPassType.GENERAL_WEB,
                            SearchFreshness.YEAR,
                            variant.scope,
                        ),
                        content_attempt_cap=exact_content_cap,
                    )
                    if not needs_more_for_qa():
                        break

        if needs_more_for_qa() and bounded.max_variant_queries:
            variant_geography = variants[0]
            for title in plan.target_title_variants[: bounded.max_variant_queries]:
                if not needs_more_for_qa():
                    break
                query = build_you_ats_query(
                    title,
                    variant_geography.location_phrase,
                    plan.target_seniority,
                )
                await run_pass(
                    request(
                        query,
                        SearchPassType.TARGET_VARIANT,
                        SearchFreshness.MONTH,
                        variant_geography.scope,
                    )
                )

        target_evidence_so_far = sum(
            item.title_match_kind == "DESCRIPTION_SUPPORTED_SPECIALTY"
            or assess_title(
                item.normalized_title or item.original_title,
                plan.search_title or "",
            )
            in {PostingTitleMatch.EXACT_TARGET, PostingTitleMatch.TARGET_VARIANT}
            for item in postings
        )
        if (
            plan.expansion_permitted
            and target_evidence_so_far < bounded.expansion_threshold
            and metrics.content_attempts < bounded.max_content_fetches
            and unique_posting_count() < bounded.target_posting_count
        ):
            metrics.expansion_triggered = True
            related_titles = observed_related_titles(
                metrics.observed_related_posting_titles,
                plan.search_title or plan.target_role or "",
                limit=bounded.max_expansion_queries,
            )
            metrics.expansion_titles = related_titles
            freshness = (
                SearchFreshness.YEAR if metrics.freshness_fallback_used else SearchFreshness.MONTH
            )
            logger.info(
                "market_related_expansion triggered=true query_count=%d", len(related_titles)
            )
            for related_title in related_titles:
                if (
                    unique_posting_count() >= bounded.target_posting_count
                    or metrics.content_attempts >= bounded.max_content_fetches
                ):
                    break
                query = build_related_query(related_title, plan.geography)
                expansion_scope = variants[0].scope
                try:
                    await run_pass(
                        request(
                            query,
                            SearchPassType.RELATED_TITLE,
                            freshness,
                            expansion_scope,
                        )
                    )
                except MarketAuthenticationError:
                    raise
                except MarketIntelligenceError as error:
                    logger.warning("market_related_search_failed category=%s", type(error).__name__)
                    metrics.limitations.append(
                        f'Related-title search for "{related_title}" could not be completed.'
                    )
        else:
            logger.info("market_related_expansion triggered=false query_count=0")

    snapshot = _snapshot(
        plan=plan,
        postings=postings,
        sources=sources,
        metrics=metrics,
        search_date=timestamp.date(),
    )
    logger.info(
        "market_search_completed query_count=%d result_count=%d retrieved_page_count=%d "
        "validated_posting_count=%d rejected_result_count=%d duplicate_count=%d latency_ms=%d",
        metrics.search_attempts,
        observed_result_count,
        metrics.content_successes,
        snapshot.validated_posting_count,
        metrics.rejected_results,
        metrics.duplicate_count,
        (perf_counter() - started) * 1000,
    )
    return MarketRetrievalResult(
        plan=plan,
        snapshot=snapshot,
        sources=sources,
        source_contents=source_contents,
        postings=postings,
        rejected_result_count=metrics.rejected_results,
        exact_search_queries=metrics.exact_search_queries,
        exact_raw_result_count=metrics.exact_raw_result_count,
        exact_title_validated_count=snapshot.exact_title_count,
        target_variant_search_queries=metrics.target_variant_search_queries,
        target_variant_raw_result_count=metrics.target_variant_raw_result_count,
        target_variant_validated_count=snapshot.target_variant_count,
        expansion_triggered=metrics.expansion_triggered,
        expansion_titles=metrics.expansion_titles,
        related_search_queries=metrics.related_search_queries,
        related_raw_result_count=metrics.related_raw_result_count,
        related_title_validated_count=snapshot.related_title_count,
        geography_out_of_scope_count=metrics.geography_out_of_scope_count,
        geography_unclear_count=metrics.geography_unclear_count,
        raw_source_count=metrics.content_successes,
        segmented_candidate_count=metrics.segmented_candidate_count,
        title_grounded_candidate_count=metrics.title_grounded_candidate_count,
        geography_valid_candidate_count=metrics.geography_valid_candidate_count,
        rejected_url_like_title_count=metrics.rejected_url_like_title_count,
        total_unique_retained_posting_count=snapshot.validated_posting_count,
        search_passes=metrics.search_passes,
        freshness_fallback_used=metrics.freshness_fallback_used,
        aggregator_result_count=metrics.aggregator_result_count,
        direct_page_count=metrics.direct_page_count,
        geography_valid_postings_by_scope=dict(
            Counter(
                posting.matched_geography_scope
                for posting in postings
                if posting.matched_geography_scope is not None
            )
        ),
    )
