"""Primary Adzuna retrieval with bounded, non-destructive You.com support."""

from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

from ai_career_navigator.domain import ConfidenceLevel, JobPosting, SourceRecord
from ai_career_navigator.market.currentness import currentness_rejection
from ai_career_navigator.market.deduplication import same_vacancy
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
    PostingContentQuality,
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
from ai_career_navigator.market.source_registry import looks_like_individual_job_url
from ai_career_navigator.market.validation import observed_related_titles, title_equivalence_reason


def _needs_enrichment(result: StructuredJobResult, *, thin_description_characters: int) -> bool:
    return (
        result.content_complete is False
        or len(result.description.strip()) <= thin_description_characters
        or result.company is None
        or result.location is None
        or result.created is None
    )


def _content_quality(page: MarketPageContent, threshold: int = 500) -> PostingContentQuality:
    text = page.markdown.strip()
    if not text:
        return PostingContentQuality.UNKNOWN
    if len(text) <= threshold or page.content_complete is False:
        return PostingContentQuality.SHORT_EXCERPT
    # Length does not prove that a source supplied a complete vacancy body.
    if page.content_complete is True:
        return PostingContentQuality.FULL_POSTING
    return PostingContentQuality.UNKNOWN


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
        active_status=result.active_status or "PROVIDER_OBSERVED",
        requisition_id=result.requisition_id,
        closing_date=result.closing_date.isoformat() if result.closing_date else None,
        content_complete=result.content_complete,
    )
    posting = JobPosting(
        source_id=source.source_id,
        original_title=normalize_whitespace(result.title),
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
        active_status=result.active_status or "PROVIDER_OBSERVED",
        requisition_id=result.requisition_id,
        canonical_job_url=url,
        content_fingerprint=sha256(normalize_whitespace(result.description).encode()).hexdigest()
        if len(result.description.strip()) >= 100
        else None,
        discovered_at=retrieved_at,
        currentness_basis="PROVIDER_SEARCH_RESULT",
        closing_date=result.closing_date,
        title_match_kind=title_equivalence_reason(result.title, target_role, result.description)
        or assessment.title_match.value,
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
        content_quality=_content_quality(page, thin_description_characters),
        limitations=[
            "Posting was observed in provider search; "
            "employer-page active status is not independently verified."
        ],
    )


def _identity_conflict(primary: MarketPostingEvidence, support: MarketPageContent) -> str | None:
    if (
        primary.posting.requisition_id
        and support.requisition_id
        and primary.posting.requisition_id != support.requisition_id
    ):
        return "REQUISITION_CONFLICT"

    def grounded(value: str | None) -> bool:
        if not value:
            return False
        normalized_value = " ".join(re.findall(r"[a-z0-9]+", value.casefold()))
        normalized_page = " ".join(re.findall(r"[a-z0-9]+", support.markdown.casefold()))
        return bool(normalized_value) and normalized_value in normalized_page

    title_matches = bool(support.title) and assess_title(
        support.title, primary.posting.original_title, posting_text=support.markdown
    ) in {
        PostingTitleMatch.EXACT_TARGET,
        PostingTitleMatch.TARGET_VARIANT,
    }
    # Content tools sometimes return a generic employer-page HTML title. That
    # metadata must not defeat an exact posting URL whose body explicitly
    # grounds the Adzuna posting title.
    if not title_matches and not grounded(primary.posting.original_title):
        return "TITLE_NOT_GROUNDED"
    left = normalize_employer(primary.posting.employer)
    right = normalize_employer(support.employer)
    if left and right and left.casefold() != right.casefold():
        return "EMPLOYER_CONFLICT"
    location_conflicts = (
        primary.posting.location
        and support.location
        and assess_geography(support.location, primary.posting.location)
        is PostingGeographyStatus.OUT_OF_SCOPE
    )
    if location_conflicts:
        return "LOCATION_CONFLICT"
    # A redirect to a general page is not the same vacancy just because fields are absent.
    same_url = canonicalize_url(str(primary.primary_source.url)) == canonicalize_url(support.url)
    if not same_url and not (
        (left and right and left.casefold() == right.casefold() or grounded(left))
        and (
            assess_geography(support.location, primary.posting.location)
            is PostingGeographyStatus.IN_SCOPE
            or (not support.location and grounded(primary.posting.location))
        )
    ):
        return "REDIRECT_IDENTITY_NOT_GROUNDED"
    return None


def _same_posting(primary: MarketPostingEvidence, support: MarketPageContent) -> bool:
    return _identity_conflict(primary, support) is None


async def _enrich(
    evidence: MarketPostingEvidence,
    client: MarketSearchClient,
    *,
    thin_description_characters: int = 500,
) -> MarketPostingEvidence:
    target_url = str(evidence.primary_source.url)
    try:
        page = await client.fetch_content(target_url)
    except MarketIntelligenceError as error:
        return evidence.model_copy(
            update={
                "enrichment_status": EnrichmentStatus.FAILED,
                "enrichment_target_url": target_url,
                "enrichment_failure_category": type(error).__name__,
                "enrichment_reason": "CONTENT_FETCH_FAILED",
                "limitations": [*evidence.limitations, "You.com enrichment was unavailable."],
            }
        )
    evidence = evidence.model_copy(
        update={
            "enrichment_observation": {
                "returned_url": page.url[:4000],
                "title": (page.title or "")[:500],
                "employer": (page.employer or "")[:500],
                "location": (page.location or "")[:500],
                "requisition_id": (page.requisition_id or "")[:200],
                "body_characters": len(page.markdown),
                "content_complete": page.content_complete,
            }
        }
    )
    conflict = _identity_conflict(evidence, page)
    if conflict:
        return evidence.model_copy(
            update={
                "enrichment_status": EnrichmentStatus.CONFLICT_REJECTED,
                "enrichment_target_url": target_url,
                "enrichment_reason": conflict,
                "limitations": [
                    *evidence.limitations,
                    "Supporting source conflicted with Adzuna title or employer fields.",
                ],
            }
        )
    if not page.markdown.strip():
        return evidence.model_copy(
            update={
                "enrichment_status": EnrichmentStatus.FAILED,
                "enrichment_target_url": target_url,
                "enrichment_failure_category": "EMPTY_CONTENT",
                "enrichment_reason": "EMPTY_CONTENT",
            }
        )
    prior_text = normalize_whitespace(evidence.primary_content.markdown)
    new_text = normalize_whitespace(page.markdown)
    blocked_shell = len(new_text) < 1000 and re.search(
        r"enable\s+javascript|access\s+denied|captcha|sign in to (?:view|continue)", new_text, re.I
    )
    if (
        new_text == prior_text
        or (new_text and new_text in prior_text)
        or (len(new_text) < len(prior_text) and page.content_complete is not True)
        or blocked_shell
    ):
        return evidence.model_copy(
            update={
                "enrichment_status": EnrichmentStatus.FAILED,
                "enrichment_target_url": target_url,
                "enrichment_failure_category": "BLOCKED_CONTENT"
                if blocked_shell
                else "NO_ADDITIONAL_CONTENT",
                "enrichment_reason": "BLOCKED_CONTENT"
                if blocked_shell
                else "NO_ADDITIONAL_CONTENT",
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
            # One selected vacancy body: do not duplicate snippets or append page boilerplate.
            "markdown": page.markdown[:40_000],
            "content_complete": False if len(page.markdown) > 40_000 else page.content_complete,
            "canonical_job_url": page.canonical_job_url or page.url,
            "closing_date": page.closing_date or evidence.primary_content.closing_date,
        }
    )
    return evidence.model_copy(
        update={
            "primary_content": combined,
            "supporting_sources": [*evidence.supporting_sources, supporting],
            "supporting_contents": [evidence.primary_content, *evidence.supporting_contents, page],
            "selected_content_source": MarketSourceProvider.YOU,
            "enrichment_status": EnrichmentStatus.APPLIED,
            "enrichment_target_url": target_url,
            "enrichment_reason": "IDENTITY_VALIDATED_CONTENT_ADDED",
            "content_quality": _content_quality(combined, thin_description_characters),
            "posting": evidence.posting.model_copy(
                update={
                    "canonical_job_url": (
                        canonicalize_url(page.canonical_job_url or page.url)
                        if looks_like_individual_job_url(page.canonical_job_url or page.url)
                        else evidence.posting.canonical_job_url
                    ),
                    "requisition_id": page.requisition_id or evidence.posting.requisition_id,
                    "content_fingerprint": sha256(
                        normalize_whitespace(combined.markdown).encode()
                    ).hexdigest(),
                    "active_status": page.active_status or evidence.posting.active_status,
                    "currentness_checked_at": evidence.posting.retrieved_at,
                    "currentness_basis": "RETRIEVED_PAGE_STATUS"
                    if page.active_status
                    else "UNKNOWN",
                }
            ),
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
                content_quality=_content_quality(retained.content),
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
    # A preferred host does not make a thin excerpt better than an actual vacancy body.
    body_rank = (
        3
        if item.content_quality is PostingContentQuality.FULL_POSTING
        else 2
        if len(text.strip()) > 500
        and item.content_quality is not PostingContentQuality.SHORT_EXCERPT
        else 1
        if text.strip()
        else 0
    )
    freshness = item.posting.posting_date.toordinal() if item.posting.posting_date else 0
    return body_rank, section_signal, source_rank, freshness


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
    duplicate_count = 0
    for item in items:
        index = next(
            (i for i, prior in enumerate(retained) if same_vacancy(prior.posting, item.posting)),
            None,
        )
        if index is None:
            retained.append(item)
            continue
        duplicate_count += 1
        current = retained[index]
        winner, loser = (
            (item, current) if _content_score(item) > _content_score(current) else (current, item)
        )
        providers = list(dict.fromkeys([*current.provider_sources, *item.provider_sources]))
        structured = max(
            (record for record in (current, item) if record.primary_source.source_type == "ADZUNA"),
            key=_content_score,
            default=winner,
        )
        conflicting_support = (
            structured.primary_source.source_type == "ADZUNA"
            and winner.primary_source.source_type != "ADZUNA"
            and not _same_posting(structured, winner.primary_content)
        )
        if conflicting_support:
            winner = structured
        field_provider = (
            MarketSourceProvider.ADZUNA
            if structured.primary_source.source_type == "ADZUNA"
            else winner.selected_content_source or MarketSourceProvider.YOU
        )
        sources = {
            str(source.source_id): source
            for source in [
                current.primary_source,
                *current.supporting_sources,
                item.primary_source,
                *item.supporting_sources,
            ]
            if source.source_id != structured.primary_source.source_id
        }
        retained[index] = structured.model_copy(
            update={
                "provider_sources": providers,
                "primary_content": winner.primary_content,
                "supporting_sources": list(sources.values()),
                "supporting_contents": [
                    current.primary_content,
                    *current.supporting_contents,
                    item.primary_content,
                    *item.supporting_contents,
                ],
                "selected_content_source": winner.selected_content_source
                or winner.provider_sources[0],
                "content_quality": winner.content_quality,
                "field_sources": {
                    field: field_provider
                    for field in ("title", "employer", "location", "posting_date")
                },
                "field_conflicts": list(
                    dict.fromkeys(
                        [
                            *current.field_conflicts,
                            *item.field_conflicts,
                            *[
                                field
                                for field in (
                                    "original_title",
                                    "employer",
                                    "location",
                                    "posting_date",
                                )
                                if getattr(current.posting, field)
                                and getattr(item.posting, field)
                                and getattr(current.posting, field) != getattr(item.posting, field)
                            ],
                        ]
                    )
                ),
                "limitations": list(
                    dict.fromkeys(
                        [
                            *current.limitations,
                            *item.limitations,
                            *(
                                [
                                    "Conflicting cross-source description was excluded; "
                                    "structured posting fields were preserved."
                                ]
                                if conflicting_support
                                else []
                            ),
                        ]
                    )
                ),
            }
        )
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
    desired_seniority = classify_seniority(target_seniority) if target_seniority else None

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
    observed: list[MarketPostingEvidence] | None = None,
) -> list[PostingRetrievalAudit]:
    selected_by_url = {
        canonicalize_url(str(source.url)): item
        for item in selected
        for source in [item.primary_source, *item.supporting_sources]
    }
    selected_by_id = {str(item.posting.posting_id): item for item in selected}
    observed_by_id = {str(item.posting.posting_id): item for item in observed or selected}
    output: list[PostingRetrievalAudit] = []
    for audit in audits:
        retained = selected_by_id.get(audit.posting_id or "") or selected_by_url.get(
            canonicalize_url(audit.source_url)
        )
        completed = retained or observed_by_id.get(audit.posting_id or "")
        if completed is not None:
            audit = audit.model_copy(
                update={
                    "content_quality": completed.content_quality,
                    "input_description_characters": len(completed.primary_content.markdown),
                    "enrichment_status": completed.enrichment_status,
                    "enrichment_target_url": completed.enrichment_target_url,
                    "enrichment_failure_category": completed.enrichment_failure_category,
                    "enrichment_reason": completed.enrichment_reason,
                    "enrichment_deferred_reason": completed.enrichment_deferred_reason,
                    "enrichment_observation": completed.enrichment_observation,
                }
            )
        if audit.rejection_reason:
            output.append(audit)
            continue
        if retained is None or audit.rejection_reason:
            output.append(audit.model_copy(update={"selected_for_primary_evidence": False}))
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
                    "content_quality": retained.content_quality,
                    "input_description_characters": len(retained.primary_content.markdown),
                    "enrichment_status": retained.enrichment_status,
                    "enrichment_target_url": retained.enrichment_target_url,
                    "enrichment_failure_category": retained.enrichment_failure_category,
                    "enrichment_reason": retained.enrichment_reason,
                    "enrichment_deferred_reason": retained.enrichment_deferred_reason,
                    "enrichment_observation": retained.enrichment_observation,
                    "selected_for_primary_evidence": retained.title_classification
                    in {"EXACT_TARGET", "TARGET_VARIANT"},
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
    if not adzuna_count and not you_count:
        return ConfidenceLevel.INSUFFICIENT, "Neither discovery lane retained a validated posting."
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


def _failed_structured_pass(
    request: StructuredJobSearchRequest, error: MarketIntelligenceError
) -> SearchPassReport:
    return SearchPassReport(
        provider=MarketSourceProvider.ADZUNA,
        request_parameters=request.model_dump(mode="json"),
        succeeded=False,
        failure_category=type(error).__name__,
        pass_type=request.pass_type,
        freshness=SearchFreshness.MONTH,
        query=f"{request.title} | {request.location} | page {request.page}",
        raw_result_count=0,
        validated_posting_count=0,
        aggregator_result_count=0,
        direct_page_count=0,
        geography_scope=request.geography_scope,
        geography_valid_posting_count=0,
    )


async def retrieve_combined_market(
    goal,
    primary_client: StructuredJobSearchClient,
    *,
    enrichment_client: MarketSearchClient | None = None,
    limits: SearchLimits | None = None,
    now: datetime | None = None,
    max_pages: int = 2,
    max_enrichments: int | None = None,
) -> MarketRetrievalResult:
    """Run Adzuna and You.com discovery concurrently, then merge validated evidence."""

    plan = build_search_plan(goal)
    if plan.status is SearchPlanStatus.SEARCH_PLAN_REQUIRES_ROLE_DISCOVERY:
        return MarketRetrievalResult(plan=plan, primary_provider=MarketSourceProvider.ADZUNA)
    bounded = limits or SearchLimits()
    you_search_budget = (
        min(3, bounded.max_search_queries, bounded.max_total_search_calls - 1)
        if enrichment_client
        else 0
    )
    adzuna_search_budget = bounded.max_total_search_calls - you_search_budget
    enrichment_budget = max_enrichments if max_enrichments is not None else bounded.max_enrichments
    if enrichment_budget is None:
        enrichment_budget = bounded.analysis_posting_limit
    enrichment_budget = min(enrichment_budget, bounded.max_content_fetches)
    you_content_budget = max(
        1,
        bounded.max_content_fetches
        - min(enrichment_budget, max(0, bounded.max_content_fetches - 1)),
    )
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
                limits=bounded.model_copy(
                    update={
                        "max_search_queries": you_search_budget,
                        "max_content_fetches": you_content_budget,
                    }
                ),
                now=timestamp,
                ats_primary=True,
            )
        )
        if enrichment_client is not None
        else None
    )

    def target_count() -> int:
        return sum(
            item.title_classification
            in {PostingTitleMatch.EXACT_TARGET.value, PostingTitleMatch.TARGET_VARIANT.value}
            for item in _merge_duplicate_evidence(evidence)[0]
        )

    try:
        async with primary_client:
            for title_index, title in enumerate(titles[: 1 + bounded.max_variant_queries]):
                for page_number in range(1, max_pages + 1):
                    if (
                        target_count() >= bounded.target_posting_count
                        or metrics.search_attempts >= adzuna_search_budget
                    ):
                        break
                    metrics.search_attempts += 1
                    search_request = StructuredJobSearchRequest(
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
                    try:
                        response = await primary_client.search_page(search_request)
                    except MarketIntelligenceError as error:
                        metrics.search_passes.append(_failed_structured_pass(search_request, error))
                        raise
                    metrics.search_successes += 1
                    metrics.malformed_response_count += response.malformed_result_count
                    metrics.structured_content_attempts += len(response.results)
                    metrics.structured_content_successes += sum(
                        bool(item.description.strip()) for item in response.results
                    )
                    metrics.discovered_urls.update(
                        url for item in response.results if (url := canonicalize_url(item.url))
                    )
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
                        currentness_error = currentness_rejection(
                            MarketPageContent(
                                url=result.url,
                                markdown=result.description,
                                posting_date=result.created.isoformat() if result.created else None,
                                closing_date=result.closing_date.isoformat()
                                if result.closing_date
                                else None,
                                active_status=result.active_status,
                            ),
                            as_of=timestamp.date(),
                            max_age_days=bounded.max_posting_age_days,
                        )
                        if currentness_error:
                            metrics.rejected_results += 1
                            metrics.posting_audits.append(
                                PostingRetrievalAudit(
                                    provider=MarketSourceProvider.ADZUNA,
                                    source_url=result.url,
                                    title=result.title,
                                    source_type=PostingSourceType.STRUCTURED_JOB,
                                    stage="CURRENTNESS",
                                    decision_unit="SEARCH_RESULT",
                                    parent_result_id=f"ADZUNA:{result.provider_job_id}",
                                    rejection_reason=currentness_error,
                                )
                            )
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
                            assess_title(
                                item.posting.original_title,
                                plan.search_title or "",
                                posting_text=item.primary_content.markdown,
                            )
                            is PostingTitleMatch.IRRELEVANT
                        ):
                            metrics.rejected_results += 1
                            continue
                        evidence.append(item)
                    metrics.search_passes.append(
                        SearchPassReport(
                            provider=MarketSourceProvider.ADZUNA,
                            request_parameters=search_request.model_dump(mode="json"),
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
                if target_count() >= bounded.target_posting_count:
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
                    if metrics.search_attempts >= adzuna_search_budget:
                        break
                    metrics.search_attempts += 1
                    search_request = StructuredJobSearchRequest(
                        title=related_title,
                        location=location,
                        page=1,
                        results_per_page=bounded.discovery_result_count,
                        pass_type=SearchPassType.RELATED_TITLE,
                        geography_scope=scope,
                    )
                    try:
                        response = await primary_client.search_page(search_request)
                    except MarketIntelligenceError as error:
                        metrics.search_passes.append(_failed_structured_pass(search_request, error))
                        raise
                    metrics.search_successes += 1
                    metrics.related_search_queries.append(related_title)
                    metrics.related_raw_result_count += len(response.results)
                    metrics.malformed_response_count += response.malformed_result_count
                    metrics.structured_content_attempts += len(response.results)
                    metrics.structured_content_successes += sum(
                        bool(item.description.strip()) for item in response.results
                    )
                    metrics.discovered_urls.update(
                        url for item in response.results if (url := canonicalize_url(item.url))
                    )
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
                            provider=MarketSourceProvider.ADZUNA,
                            request_parameters=search_request.model_dump(mode="json"),
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

    adzuna_search_count = metrics.search_attempts
    adzuna_raw_result_count = (
        metrics.exact_raw_result_count
        + metrics.target_variant_raw_result_count
        + metrics.related_raw_result_count
    )
    adzuna_validated_count = len(_merge_duplicate_evidence(evidence)[0])
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
            parent_result_id=str(item.primary_source.url),
            title_match_kind=item.posting.title_match_kind,
        )
        for item in evidence
    ]
    you_result: MarketRetrievalResult | None = None
    if you_task is not None:
        try:
            you_result = await you_task
            you_failed = bool(
                you_result.snapshot
                and you_result.snapshot.search_query_count
                and not you_result.snapshot.successful_search_query_count
            )
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
    # Order the complete pool; fetch useful missing content before the final bounded selection.
    evidence = _select_diverse_evidence(
        evidence, len(evidence), plan.target_seniority or plan.search_title
    )

    enrichment_attempts = 0
    if enrichment_client is not None:
        async with enrichment_client:
            updated: list[MarketPostingEvidence] = []
            for item in evidence:
                if (
                    item.enrichment_status is EnrichmentStatus.NOT_ATTEMPTED
                    and item.title_classification in {"EXACT_TARGET", "TARGET_VARIANT"}
                    and enrichment_attempts
                    < min(
                        enrichment_budget,
                        bounded.max_content_fetches
                        - (
                            you_result.snapshot.content_fetch_count
                            if you_result and you_result.snapshot
                            else 0
                        ),
                    )
                ):
                    enrichment_attempts += 1
                    metrics.content_attempts += 1
                    item = await _enrich(
                        item,
                        enrichment_client,
                        thin_description_characters=bounded.thin_description_characters,
                    )
                    if item.enrichment_status is EnrichmentStatus.APPLIED:
                        metrics.content_successes += 1
                    elif item.enrichment_status is EnrichmentStatus.FAILED:
                        metrics.content_failure_count += 1
                elif item.enrichment_status is EnrichmentStatus.NOT_ATTEMPTED:
                    item = item.model_copy(
                        update={
                            "enrichment_target_url": str(item.primary_source.url),
                            "enrichment_deferred_reason": (
                                "NOT_PRIMARY_TARGET_COHORT"
                                if item.title_classification
                                not in {"EXACT_TARGET", "TARGET_VARIANT"}
                                else "ENRICHMENT_BUDGET_EXHAUSTED"
                                if enrichment_attempts >= enrichment_budget
                                else "SHARED_CONTENT_FETCH_BUDGET_EXHAUSTED"
                            ),
                        }
                    )
                updated.append(item)
            evidence = updated
    else:
        evidence = [
            item.model_copy(
                update={
                    "enrichment_target_url": str(item.primary_source.url),
                    "enrichment_deferred_reason": "CONTENT_PROVIDER_NOT_CONFIGURED",
                }
            )
            if item.enrichment_status is EnrichmentStatus.NOT_ATTEMPTED
            else item
            for item in evidence
        ]

    completion_evidence = list(evidence)
    current_evidence = []
    for item in evidence:
        rejection = currentness_rejection(
            item.primary_content.model_copy(update={"active_status": item.posting.active_status}),
            as_of=timestamp.date(),
            max_age_days=bounded.max_posting_age_days,
        )
        if rejection:
            metrics.rejected_candidates += 1
            metrics.posting_audits.append(
                PostingRetrievalAudit(
                    provider=item.provider_sources[0],
                    source_url=str(item.primary_source.url),
                    source_type=item.source_type,
                    title=item.posting.original_title,
                    posting_id=str(item.posting.posting_id),
                    rejection_reason=rejection,
                    stage="CURRENTNESS_AFTER_ENRICHMENT",
                    parent_result_id=str(item.primary_source.url),
                )
            )
        else:
            current_evidence.append(item)
    # Completion may resolve formerly distinct redirect URLs to the same real vacancy.
    evidence, completion_duplicates = _merge_duplicate_evidence(current_evidence)
    metrics.duplicate_count += completion_duplicates
    cross_source_match_count = sum(len(item.provider_sources) > 1 for item in evidence)
    primary = [
        item for item in evidence if item.title_classification in {"EXACT_TARGET", "TARGET_VARIANT"}
    ]
    context = [item for item in evidence if item.title_classification == "RELATED_TITLE"]
    evidence = _select_diverse_evidence(
        primary, bounded.target_posting_count, plan.target_seniority or plan.search_title
    ) + _select_diverse_evidence(
        context,
        bounded.max_expansion_queries if plan.expansion_permitted else 0,
        plan.target_seniority or plan.search_title,
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
                *metrics.posting_audits,
                *adzuna_audits,
                *(you_result.posting_audits if you_result is not None else []),
            ],
            evidence,
            completion_evidence,
        ),
        you_raw_result_count=(you_result.you_raw_result_count if you_result else 0),
        you_direct_posting_count=(you_result.you_direct_posting_count if you_result else 0),
        you_context_result_count=(you_result.you_context_result_count if you_result else 0),
        you_rejected_result_count=(you_result.you_rejected_result_count if you_result else 0),
        you_fallback_triggered=(you_result.you_fallback_triggered if you_result else False),
        rejected_candidate_count=metrics.rejected_candidates
        + (you_result.rejected_candidate_count if you_result else 0),
        fetch_failure_count=metrics.content_failure_count,
        unique_url_count=len(
            metrics.discovered_urls
            | {audit.source_url for audit in (you_result.posting_audits if you_result else [])}
        ),
        budget_deferred_result_count=you_result.budget_deferred_result_count if you_result else 0,
        effective_budgets={
            "total_search_calls": bounded.max_total_search_calls,
            "adzuna_search_calls": adzuna_search_budget,
            "you_search_calls": you_search_budget,
            "content_fetches": bounded.max_content_fetches,
            "enrichment_attempts": enrichment_budget,
            "max_posting_age_days": bounded.max_posting_age_days,
            "max_retries_per_call": bounded.max_retries,
        },
    )
