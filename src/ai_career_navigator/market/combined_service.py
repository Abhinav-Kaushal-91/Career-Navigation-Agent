"""Primary Adzuna retrieval with bounded, non-destructive You.com support."""

from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from ai_career_navigator.domain import ConfidenceLevel, JobPosting, SourceRecord
from ai_career_navigator.market.deduplication import deduplicate_postings
from ai_career_navigator.market.errors import MarketIntelligenceError
from ai_career_navigator.market.mcp.protocol import MarketSearchClient, StructuredJobSearchClient
from ai_career_navigator.market.normalization import (
    canonicalize_url,
    normalize_employer,
    normalize_title,
    normalize_whitespace,
)
from ai_career_navigator.market.processing import (
    assess_candidate,
    assess_geography,
    assess_title,
    classify_seniority,
)
from ai_career_navigator.market.requirement_schemas import (
    PostingCandidate,
    PostingGeographyStatus,
    PostingTitleMatch,
)
from ai_career_navigator.market.schemas import (
    EnrichmentStatus,
    MarketPageContent,
    MarketPostingEvidence,
    MarketRetrievalResult,
    MarketSourceProvider,
    PostingRetrievalAudit,
    PostingSourceType,
    RetainedSourceContent,
    RetrievalQuality,
    SearchFreshness,
    SearchLimits,
    SearchPassReport,
    SearchPassType,
    SearchPlanStatus,
    StructuredJobResult,
    StructuredJobSearchRequest,
)
from ai_career_navigator.market.search_plan import build_search_plan
from ai_career_navigator.market.service import _RunMetrics, _snapshot, retrieve_current_market
from ai_career_navigator.market.validation import observed_related_titles


def _needs_enrichment(result: StructuredJobResult, *, thin_description_characters: int) -> bool:
    return (
        len(result.description.strip()) <= thin_description_characters
        or result.company is None
        or result.location is None
        or result.created is None
    )


def _work_mode(description: str) -> str | None:
    folded = description.casefold()
    if "remote" in folded:
        return "Remote"
    if "hybrid" in folded:
        return "Hybrid"
    if "on-site" in folded or "onsite" in folded:
        return "On-site"
    return None


def _structured_candidate(result: StructuredJobResult) -> PostingCandidate:
    evidence = result.location
    return PostingCandidate(
        source_id=uuid4(),
        source_reference=" > ".join(
            part for part in (result.company, result.title, result.location) if part
        ),
        source_reference_text=normalize_whitespace(
            " ".join(
                part
                for part in (
                    result.title,
                    result.company,
                    result.location,
                    result.description[:1500],
                )
                if part
            )
        ),
        title=result.title,
        employer=result.company,
        location=result.location,
        location_evidence_text=evidence,
        posting_text=result.description[:20_000],
        extraction_confidence=ConfidenceLevel.HIGH,
    )


def _primary_evidence(
    result: StructuredJobResult,
    *,
    goal_geography: str,
    requested_scope,  # type: ignore[no-untyped-def]
    retrieved_at: datetime,
    thin_description_characters: int,
    target_role: str,
    target_seniority: str | None,
) -> MarketPostingEvidence | None:
    candidate = _structured_candidate(result)
    assessment = assess_candidate(
        candidate,
        target_role=target_role,
        target_geography=goal_geography,
        requested_geography_scope=requested_scope,
        target_seniority=target_seniority,
    )
    if assessment.geography_status is not PostingGeographyStatus.IN_SCOPE:
        return None
    url = canonicalize_url(result.url)
    if url is None:
        return None
    source = SourceRecord(
        source_id=candidate.source_id,
        source_type=MarketSourceProvider.ADZUNA.value,
        title=normalize_title(result.title),
        url=url,
        employer=normalize_employer(result.company),
        geography=normalize_whitespace(result.location) if result.location else None,
        retrieval_date=retrieved_at.date(),
        publication_date=result.created,
    )
    page = MarketPageContent(
        url=url,
        title=result.title,
        markdown=result.description,
        employer=result.company,
        location=result.location,
        work_mode=_work_mode(result.description),
        employment_type=result.contract_type,
        posting_date=result.created.isoformat() if result.created else None,
        active_status="ACTIVE",
    )
    posting = JobPosting(
        source_id=source.source_id,
        original_title=normalize_title(result.title),
        normalized_title=normalize_title(result.title),
        employer=normalize_employer(result.company),
        location=normalize_whitespace(result.location) if result.location else None,
        location_evidence_text=result.location,
        requested_geography_scope=requested_scope,
        matched_geography_scope=assessment.matched_geography_scope,
        grounded_location=result.location,
        work_mode=page.work_mode,
        employment_type=result.contract_type,
        posting_date=result.created,
        retrieved_at=retrieved_at,
        active_status="ACTIVE",
        extraction_confidence=ConfidenceLevel.HIGH,
    )
    return MarketPostingEvidence(
        posting=posting,
        primary_source=source,
        primary_content=page,
        enrichment_status=(
            EnrichmentStatus.NOT_ATTEMPTED
            if _needs_enrichment(result, thin_description_characters=thin_description_characters)
            else EnrichmentStatus.NOT_NEEDED
        ),
        provider_sources=[MarketSourceProvider.ADZUNA],
        source_type=PostingSourceType.STRUCTURED_JOB,
        retrieval_quality=(
            RetrievalQuality.HIGH
            if len(result.description.strip()) > thin_description_characters
            else RetrievalQuality.MODERATE
        ),
        title_classification=assessment.title_match.value,
        seniority_classification=classify_seniority(result.title),
        selected_content_source=MarketSourceProvider.ADZUNA,
    )


def _same_posting(primary: MarketPostingEvidence, support: MarketPageContent) -> bool:
    def grounded(value: str | None) -> bool:
        if not value:
            return False
        normalized_value = " ".join(re.findall(r"[a-z0-9]+", value.casefold()))
        normalized_page = " ".join(re.findall(r"[a-z0-9]+", support.markdown.casefold()))
        return bool(normalized_value) and normalized_value in normalized_page

    title_matches = not support.title or assess_title(
        support.title, primary.posting.original_title
    ) in {
        PostingTitleMatch.EXACT_TARGET,
        PostingTitleMatch.TARGET_VARIANT,
    }
    # Content tools sometimes return a generic employer-page HTML title. That
    # metadata must not defeat an exact posting URL whose body explicitly
    # grounds the Adzuna posting title.
    if not title_matches and not grounded(primary.posting.original_title):
        return False
    left = normalize_employer(primary.posting.employer)
    right = normalize_employer(support.employer)
    if left and right and left.casefold() != right.casefold() and not grounded(left):
        return False
    location_conflicts = (
        primary.posting.location
        and support.location
        and assess_geography(support.location, primary.posting.location)
        is PostingGeographyStatus.OUT_OF_SCOPE
    )
    return not (location_conflicts and not grounded(primary.posting.location))


async def _enrich(
    evidence: MarketPostingEvidence,
    client: MarketSearchClient,
) -> MarketPostingEvidence:
    try:
        page = await client.fetch_content(str(evidence.primary_source.url))
    except MarketIntelligenceError:
        return evidence.model_copy(
            update={
                "enrichment_status": EnrichmentStatus.FAILED,
                "limitations": [*evidence.limitations, "You.com enrichment was unavailable."],
            }
        )
    if not _same_posting(evidence, page):
        return evidence.model_copy(
            update={
                "enrichment_status": EnrichmentStatus.CONFLICT_REJECTED,
                "limitations": [
                    *evidence.limitations,
                    "Supporting source conflicted with Adzuna title or employer fields.",
                ],
            }
        )
    supporting = SourceRecord(
        source_type=MarketSourceProvider.YOU.value,
        title=page.title or evidence.primary_source.title,
        url=page.url,
        employer=page.employer,
        geography=page.location,
        retrieval_date=evidence.primary_source.retrieval_date,
        publication_date=evidence.primary_source.publication_date,
    )
    combined = evidence.primary_content.model_copy(
        update={
            "markdown": (
                f"{evidence.primary_content.markdown}\n\n"
                "--- Supporting source evidence ---\n"
                f"{page.markdown}"
            )[:40_000]
        }
    )
    return evidence.model_copy(
        update={
            "primary_content": combined,
            "supporting_sources": [supporting],
            "supporting_contents": [page],
            "enrichment_status": EnrichmentStatus.APPLIED,
        }
    )


def _you_posting_evidence(result: MarketRetrievalResult) -> list[MarketPostingEvidence]:
    """Convert independently validated You.com records into the combined provenance model."""

    contents = {item.source.source_id: item for item in result.source_contents}
    evidence: list[MarketPostingEvidence] = []
    audits = {
        audit.posting_id: audit for audit in result.posting_audits if audit.posting_id is not None
    }
    for posting in result.postings:
        retained = contents.get(posting.source_id)
        if retained is None:
            continue
        source = retained.source.model_copy(update={"source_type": MarketSourceProvider.YOU.value})
        audit = audits.get(str(posting.posting_id))
        evidence.append(
            MarketPostingEvidence(
                posting=posting,
                primary_source=source,
                primary_content=retained.content,
                enrichment_status=EnrichmentStatus.NOT_NEEDED,
                provider_sources=[MarketSourceProvider.YOU],
                source_type=(
                    audit.source_type if audit else PostingSourceType.DIRECT_EMPLOYER_POSTING
                ),
                retrieval_quality=RetrievalQuality.HIGH,
                title_classification=(audit.title_classification if audit else None),
                seniority_classification=(
                    audit.seniority_classification
                    if audit
                    else classify_seniority(posting.original_title)
                ),
                selected_content_source=MarketSourceProvider.YOU,
            )
        )
    return evidence


def _content_score(item: MarketPostingEvidence) -> tuple[int, int, int, int]:
    source_rank = {
        PostingSourceType.DIRECT_EMPLOYER_POSTING: 4,
        PostingSourceType.DIRECT_ATS_POSTING: 3,
        PostingSourceType.STRUCTURED_JOB: 2,
        PostingSourceType.AGGREGATOR_PAGE: 1,
        PostingSourceType.BACKGROUND_CONTEXT: 0,
    }[item.source_type]
    text = item.primary_content.markdown.casefold()
    section_signal = sum(
        token in text
        for token in ("qualifications", "requirements", "responsibilities", "what you'll do")
    )
    clarity = int(bool(item.posting.original_title)) + int(bool(item.posting.employer))
    freshness = int(item.posting.posting_date is not None)
    return source_rank, section_signal, clarity, freshness


def _evidence_identity(item: MarketPostingEvidence) -> tuple[str, str, str]:
    return (
        (normalize_employer(item.posting.employer) or "").casefold(),
        normalize_title(item.posting.original_title).casefold(),
        normalize_whitespace(
            item.posting.grounded_location or item.posting.location or ""
        ).casefold(),
    )


def _merge_duplicate_evidence(
    items: list[MarketPostingEvidence],
) -> tuple[list[MarketPostingEvidence], int]:
    """Deduplicate provider-neutral postings while retaining all provenance."""

    retained: list[MarketPostingEvidence] = []
    by_url: dict[str, int] = {}
    by_identity: dict[tuple[str, str, str], int] = {}
    duplicate_count = 0
    for item in items:
        canonical = canonicalize_url(str(item.primary_source.url))
        identity = _evidence_identity(item)
        index = by_url.get(canonical or "") if canonical else None
        if index is None and all(identity):
            index = by_identity.get(identity)
        if index is None:
            index = len(retained)
            retained.append(item)
            if canonical:
                by_url[canonical] = index
            if all(identity):
                by_identity[identity] = index
            continue
        duplicate_count += 1
        current = retained[index]
        winner, loser = (
            (item, current) if _content_score(item) > _content_score(current) else (current, item)
        )
        providers = list(dict.fromkeys([*current.provider_sources, *item.provider_sources]))
        retained[index] = winner.model_copy(
            update={
                "provider_sources": providers,
                "supporting_sources": [
                    *winner.supporting_sources,
                    loser.primary_source,
                    *loser.supporting_sources,
                ],
                "supporting_contents": [
                    *winner.supporting_contents,
                    loser.primary_content,
                    *loser.supporting_contents,
                ],
                "selected_content_source": winner.provider_sources[0],
            }
        )
        if canonical:
            by_url[canonical] = index
        if all(identity):
            by_identity[identity] = index
    return retained, duplicate_count


def _select_diverse_evidence(
    items: list[MarketPostingEvidence],
    limit: int,
    target_seniority: str | None = None,
) -> list[MarketPostingEvidence]:
    title_rank = {
        PostingTitleMatch.EXACT_TARGET.value: 3,
        PostingTitleMatch.TARGET_VARIANT.value: 2,
        PostingTitleMatch.RELATED_TITLE.value: 1,
    }
    remaining = list(items)
    selected: list[MarketPostingEvidence] = []
    employers: set[str] = set()
    providers: set[MarketSourceProvider] = set()
    desired_seniority = (
        classify_seniority(target_seniority) if target_seniority else None
    )

    def seniority_rank(item: MarketPostingEvidence) -> int:
        observed = item.seniority_classification
        if desired_seniority and desired_seniority.value != "UNKNOWN":
            return 2 if observed is desired_seniority else 0
        return 2 if observed.value == "STANDARD" else 1 if observed.value == "UNKNOWN" else 0

    while remaining and len(selected) < limit:
        remaining.sort(
            key=lambda item: (
                title_rank.get(item.title_classification or "", 0),
                seniority_rank(item),
                int((normalize_employer(item.posting.employer) or "").casefold() not in employers),
                _content_score(item)[:3],
                _content_score(item)[3],
                int(any(provider not in providers for provider in item.provider_sources)),
            ),
            reverse=True,
        )
        chosen = remaining.pop(0)
        selected.append(chosen)
        employer = (normalize_employer(chosen.posting.employer) or "").casefold()
        if employer:
            employers.add(employer)
        providers.update(chosen.provider_sources)
    return selected


def _resolve_retrieval_audits(
    audits: list[PostingRetrievalAudit],
    selected: list[MarketPostingEvidence],
) -> list[PostingRetrievalAudit]:
    selected_by_identity = {_evidence_identity(item): item for item in selected}
    output: list[PostingRetrievalAudit] = []
    for audit in audits:
        identity = (
            (normalize_employer(audit.employer) or "").casefold(),
            normalize_title(audit.title).casefold(),
            normalize_whitespace(audit.location or "").casefold(),
        )
        retained = selected_by_identity.get(identity)
        if retained is None or audit.rejection_reason:
            output.append(audit)
            continue
        retained_id = str(retained.posting.posting_id)
        output.append(
            audit.model_copy(
                update={
                    "duplicate_of": (
                        retained_id
                        if audit.posting_id is not None and audit.posting_id != retained_id
                        else None
                    ),
                    "selected_content_source": retained.selected_content_source,
                    "selected_for_primary_evidence": True,
                }
            )
        )
    return output


def _merge_you_metrics(metrics: _RunMetrics, result: MarketRetrievalResult) -> None:
    """Merge observable You.com lane activity without changing validation rules."""

    snapshot = result.snapshot
    if snapshot is not None:
        metrics.search_attempts += snapshot.search_query_count
        metrics.search_successes += snapshot.successful_search_query_count
        metrics.content_attempts += snapshot.content_fetch_count
        metrics.content_successes += snapshot.successful_content_fetch_count
        metrics.malformed_response_count += max(
            0,
            snapshot.content_fetch_count - snapshot.successful_content_fetch_count,
        )
        metrics.duplicate_count += snapshot.duplicate_posting_count
    metrics.rejected_results += result.rejected_result_count
    metrics.exact_raw_result_count += result.exact_raw_result_count
    metrics.target_variant_raw_result_count += result.target_variant_raw_result_count
    metrics.related_raw_result_count += result.related_raw_result_count
    metrics.geography_out_of_scope_count += result.geography_out_of_scope_count
    metrics.geography_unclear_count += result.geography_unclear_count
    metrics.segmented_candidate_count += result.segmented_candidate_count
    metrics.title_grounded_candidate_count += result.title_grounded_candidate_count
    metrics.geography_valid_candidate_count += result.geography_valid_candidate_count
    metrics.rejected_url_like_title_count += result.rejected_url_like_title_count
    metrics.aggregator_result_count += result.aggregator_result_count
    metrics.direct_page_count += result.direct_page_count
    metrics.exact_search_queries.extend(result.exact_search_queries)
    metrics.target_variant_search_queries.extend(result.target_variant_search_queries)
    metrics.related_search_queries.extend(result.related_search_queries)
    metrics.search_passes.extend(result.search_passes)
    metrics.freshness_fallback_used = (
        metrics.freshness_fallback_used or result.freshness_fallback_used
    )


def _source_coverage(
    *,
    adzuna_failed: bool,
    you_failed: bool,
    adzuna_count: int,
    you_count: int,
    overlap_count: int,
) -> tuple[ConfidenceLevel, str]:
    if adzuna_failed and you_failed:
        return ConfidenceLevel.INSUFFICIENT, "Both discovery lanes were unavailable."
    if adzuna_failed:
        return ConfidenceLevel.LOW, "Only You.com discovery was available."
    if you_failed:
        return ConfidenceLevel.LOW, "Only Adzuna discovery was available."
    if adzuna_count and you_count:
        agreement = (
            f" {overlap_count} posting(s) were independently observed by both sources."
            if overlap_count
            else " The retained postings did not overlap across sources."
        )
        return ConfidenceLevel.MODERATE, "Both discovery lanes retained evidence." + agreement
    if adzuna_count or you_count:
        return (
            ConfidenceLevel.LOW,
            "Both discovery lanes completed, but only one retained validated postings.",
        )
    return ConfidenceLevel.INSUFFICIENT, "Neither discovery lane retained a validated posting."


async def retrieve_combined_market(
    goal,
    primary_client: StructuredJobSearchClient,
    *,
    enrichment_client: MarketSearchClient | None = None,
    limits: SearchLimits | None = None,
    now: datetime | None = None,
    max_pages: int = 2,
    max_enrichments: int = 2,
) -> MarketRetrievalResult:
    """Run Adzuna and You.com discovery concurrently, then merge validated evidence."""

    plan = build_search_plan(goal)
    if plan.status is SearchPlanStatus.SEARCH_PLAN_REQUIRES_ROLE_DISCOVERY:
        return MarketRetrievalResult(plan=plan, primary_provider=MarketSourceProvider.ADZUNA)
    bounded = limits or SearchLimits()
    timestamp = now or datetime.now(UTC)
    scope = plan.allowed_geography_scopes[0]
    location = plan.geography
    titles = [plan.search_title or plan.target_role or "", *plan.target_title_variants]
    evidence: list[MarketPostingEvidence] = []
    metrics = _RunMetrics()
    primary_failed = False
    you_failed = False
    you_task = (
        asyncio.create_task(
            retrieve_current_market(
                goal,
                enrichment_client,
                limits=bounded,
                now=timestamp,
                ats_primary=True,
            )
        )
        if enrichment_client is not None
        else None
    )

    def target_count() -> int:
        return sum(
            assess_title(item.posting.original_title, plan.search_title or "")
            in {PostingTitleMatch.EXACT_TARGET, PostingTitleMatch.TARGET_VARIANT}
            for item in evidence
        )

    try:
        async with primary_client:
            for title_index, title in enumerate(titles[: 1 + bounded.max_variant_queries]):
                for page_number in range(1, max_pages + 1):
                    if len(evidence) >= bounded.target_posting_count:
                        break
                    metrics.search_attempts += 1
                    response = await primary_client.search_page(
                        StructuredJobSearchRequest(
                            title=title,
                            location=location,
                            page=page_number,
                            results_per_page=bounded.discovery_result_count,
                            pass_type=(
                                SearchPassType.DIRECT_SOURCE
                                if title_index == 0
                                else SearchPassType.TARGET_VARIANT
                            ),
                            geography_scope=scope,
                        )
                    )
                    metrics.search_successes += 1
                    metrics.malformed_response_count += response.malformed_result_count
                    metrics.content_attempts += len(response.results)
                    metrics.content_successes += len(response.results)
                    pass_type = (
                        SearchPassType.DIRECT_SOURCE
                        if title_index == 0
                        else SearchPassType.TARGET_VARIANT
                    )
                    if title_index == 0:
                        metrics.exact_search_queries.append(title)
                        metrics.exact_raw_result_count += len(response.results)
                    else:
                        metrics.target_variant_search_queries.append(title)
                        metrics.target_variant_raw_result_count += len(response.results)
                    before = len(evidence)
                    for result in response.results:
                        if (
                            result.created
                            and result.created < (timestamp - timedelta(days=366)).date()
                        ):
                            metrics.rejected_results += 1
                            continue
                        item = _primary_evidence(
                            result,
                            goal_geography=plan.geography,
                            requested_scope=scope,
                            retrieved_at=timestamp,
                            thin_description_characters=bounded.thin_description_characters,
                            target_role=plan.search_title or plan.target_role or "",
                            target_seniority=plan.target_seniority,
                        )
                        if item is None:
                            metrics.rejected_results += 1
                            continue
                        if (
                            assess_title(item.posting.original_title, plan.search_title or "")
                            is PostingTitleMatch.IRRELEVANT
                        ):
                            metrics.rejected_results += 1
                            continue
                        evidence.append(item)
                    metrics.search_passes.append(
                        SearchPassReport(
                            pass_type=pass_type,
                            freshness=SearchFreshness.MONTH,
                            query=f"{title} | {location} | page {page_number}",
                            raw_result_count=len(response.results),
                            validated_posting_count=len(evidence) - before,
                            aggregator_result_count=0,
                            direct_page_count=len(evidence) - before,
                            geography_scope=scope,
                            geography_valid_posting_count=len(evidence) - before,
                        )
                    )
                    if (
                        not response.results
                        or len(response.results) < bounded.discovery_result_count
                    ):
                        break
                if target_count() >= 3:
                    break
            if (
                plan.expansion_permitted
                and target_count() < bounded.expansion_threshold
                and bounded.max_expansion_queries
            ):
                related_titles = observed_related_titles(
                    [
                        item.posting.original_title
                        for item in evidence
                        if assess_title(item.posting.original_title, plan.search_title or "")
                        is PostingTitleMatch.RELATED_TITLE
                    ],
                    plan.search_title or "",
                    limit=bounded.max_expansion_queries,
                )
                metrics.expansion_triggered = bool(related_titles)
                metrics.expansion_titles = related_titles
                for related_title in related_titles:
                    metrics.search_attempts += 1
                    response = await primary_client.search_page(
                        StructuredJobSearchRequest(
                            title=related_title,
                            location=location,
                            page=1,
                            results_per_page=bounded.discovery_result_count,
                            pass_type=SearchPassType.RELATED_TITLE,
                            geography_scope=scope,
                        )
                    )
                    metrics.search_successes += 1
                    metrics.related_search_queries.append(related_title)
                    metrics.related_raw_result_count += len(response.results)
                    metrics.malformed_response_count += response.malformed_result_count
                    metrics.content_attempts += len(response.results)
                    metrics.content_successes += len(response.results)
                    before = len(evidence)
                    for result in response.results:
                        item = _primary_evidence(
                            result,
                            goal_geography=plan.geography,
                            requested_scope=scope,
                            retrieved_at=timestamp,
                            thin_description_characters=bounded.thin_description_characters,
                            target_role=plan.search_title or plan.target_role or "",
                            target_seniority=plan.target_seniority,
                        )
                        if (
                            item is not None
                            and assess_title(item.posting.original_title, plan.search_title or "")
                            is PostingTitleMatch.RELATED_TITLE
                        ):
                            evidence.append(item)
                    metrics.search_passes.append(
                        SearchPassReport(
                            pass_type=SearchPassType.RELATED_TITLE,
                            freshness=SearchFreshness.MONTH,
                            query=f"{related_title} | {location} | page 1",
                            raw_result_count=len(response.results),
                            validated_posting_count=len(evidence) - before,
                            aggregator_result_count=0,
                            direct_page_count=len(evidence) - before,
                            geography_scope=scope,
                            geography_valid_posting_count=len(evidence) - before,
                        )
                    )
    except MarketIntelligenceError:
        primary_failed = True

    unique_urls: set[str] = set()
    url_deduplicated: list[MarketPostingEvidence] = []
    for item in evidence:
        url = canonicalize_url(str(item.primary_source.url))
        if url and url in unique_urls:
            metrics.duplicate_count += 1
            continue
        if url:
            unique_urls.add(url)
        url_deduplicated.append(item)
    evidence = url_deduplicated
    postings, duplicate_count = deduplicate_postings(item.posting for item in evidence)
    metrics.duplicate_count += duplicate_count
    retained_ids = {item.posting_id for item in postings}
    evidence = [item for item in evidence if item.posting.posting_id in retained_ids]

    adzuna_search_count = metrics.search_attempts
    adzuna_raw_result_count = (
        metrics.exact_raw_result_count
        + metrics.target_variant_raw_result_count
        + metrics.related_raw_result_count
    )
    adzuna_validated_count = len(evidence)
    adzuna_audits = [
        PostingRetrievalAudit(
            posting_id=str(item.posting.posting_id),
            provider=MarketSourceProvider.ADZUNA,
            source_url=str(item.primary_source.url),
            source_type=item.source_type,
            title=item.posting.original_title,
            employer=item.posting.employer,
            location=item.posting.grounded_location or item.posting.location,
            title_classification=item.title_classification,
            seniority_classification=item.seniority_classification,
            selected_content_source=MarketSourceProvider.ADZUNA,
        )
        for item in evidence
    ]
    you_result: MarketRetrievalResult | None = None
    if you_task is not None:
        try:
            you_result = await you_task
        except MarketIntelligenceError:
            you_failed = True
            metrics.limitations.append(
                "You.com parallel discovery was unavailable; Adzuna evidence was preserved."
            )

    you_evidence = _you_posting_evidence(you_result) if you_result is not None else []
    if you_result is not None:
        _merge_you_metrics(metrics, you_result)
    you_validated_count = len(you_evidence)

    combined = [*evidence, *you_evidence]
    evidence, cross_identity_duplicates = _merge_duplicate_evidence(combined)
    metrics.duplicate_count += cross_identity_duplicates
    cross_source_match_count = sum(len(item.provider_sources) > 1 for item in evidence)
    evidence = _select_diverse_evidence(
        evidence,
        bounded.target_posting_count,
        plan.target_seniority,
    )

    enrichment_attempts = 0
    if enrichment_client is not None:
        async with enrichment_client:
            updated: list[MarketPostingEvidence] = []
            for item in evidence:
                if (
                    item.enrichment_status is EnrichmentStatus.NOT_ATTEMPTED
                    and enrichment_attempts < max_enrichments
                ):
                    enrichment_attempts += 1
                    item = await _enrich(item, enrichment_client)
                updated.append(item)
            evidence = updated

    metrics.malformed_response_count += sum(
        item.enrichment_status
        in {
            EnrichmentStatus.NOT_ATTEMPTED,
            EnrichmentStatus.FAILED,
            EnrichmentStatus.CONFLICT_REJECTED,
        }
        for item in evidence
    )

    postings = [item.posting for item in evidence]
    sources = [item.primary_source for item in evidence]
    source_contents = [
        RetainedSourceContent(source=item.primary_source, content=item.primary_content)
        for item in evidence
    ]
    for item in evidence:
        metrics.limitations.extend(item.limitations)
    coverage_confidence, coverage_reason = _source_coverage(
        adzuna_failed=primary_failed,
        you_failed=you_failed,
        adzuna_count=adzuna_validated_count,
        you_count=you_validated_count,
        overlap_count=cross_source_match_count,
    )
    if primary_failed:
        metrics.limitations.append(
            "Adzuna parallel discovery was unavailable; validated You.com evidence was preserved."
        )
    snapshot = _snapshot(
        plan=plan,
        postings=postings,
        sources=sources,
        metrics=metrics,
        search_date=timestamp.date(),
    )
    return MarketRetrievalResult(
        plan=plan,
        snapshot=snapshot,
        sources=sources,
        source_contents=source_contents,
        postings=postings,
        posting_evidence=evidence,
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
        search_passes=metrics.search_passes,
        total_unique_retained_posting_count=snapshot.validated_posting_count,
        geography_valid_candidate_count=snapshot.validated_posting_count,
        primary_provider=MarketSourceProvider.ADZUNA,
        enrichment_provider=(MarketSourceProvider.YOU if enrichment_client is not None else None),
        degraded_discovery=primary_failed or you_failed,
        primary_search_count=adzuna_search_count,
        enrichment_attempt_count=enrichment_attempts,
        enrichment_success_count=sum(
            item.enrichment_status is EnrichmentStatus.APPLIED for item in evidence
        ),
        parallel_discovery=enrichment_client is not None,
        you_search_count=(
            you_result.snapshot.search_query_count
            if you_result is not None and you_result.snapshot is not None
            else 0
        ),
        adzuna_raw_result_count=adzuna_raw_result_count,
        adzuna_validated_count=adzuna_validated_count,
        you_validated_count=you_validated_count,
        cross_source_match_count=cross_source_match_count,
        source_coverage_confidence=coverage_confidence,
        source_coverage_reason=coverage_reason,
        posting_audits=_resolve_retrieval_audits(
            [
                *adzuna_audits,
                *(you_result.posting_audits if you_result is not None else []),
            ],
            evidence,
        ),
        you_raw_result_count=(you_result.you_raw_result_count if you_result else 0),
        you_direct_posting_count=(you_result.you_direct_posting_count if you_result else 0),
        you_context_result_count=(you_result.you_context_result_count if you_result else 0),
        you_rejected_result_count=(you_result.you_rejected_result_count if you_result else 0),
        you_fallback_triggered=(you_result.you_fallback_triggered if you_result else False),
    )
