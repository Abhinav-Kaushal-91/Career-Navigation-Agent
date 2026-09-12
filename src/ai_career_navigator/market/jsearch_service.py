"""Bounded JSearch-only retrieval; no web-search or legacy-provider fallback."""

from datetime import UTC, datetime

from ai_career_navigator.domain import ConfidenceLevel
from ai_career_navigator.market.combined_service import _primary_evidence
from ai_career_navigator.market.currentness import currentness_rejection
from ai_career_navigator.market.deduplication import same_vacancy
from ai_career_navigator.market.errors import (
    MarketAuthenticationError,
    MarketIntelligenceError,
    MarketRateLimitError,
)
from ai_career_navigator.market.jsearch_client import description_incomplete
from ai_career_navigator.market.requirement_schemas import PostingTitleMatch
from ai_career_navigator.market.schemas import (
    EnrichmentStatus,
    MarketRetrievalResult,
    MarketSourceProvider,
    PostingRetrievalAudit,
    PostingSourceType,
    RetainedSourceContent,
    SearchLimits,
    SearchPlanStatus,
    StructuredJobSearchRequest,
)
from ai_career_navigator.market.search_plan import build_search_plan
from ai_career_navigator.market.service import _RunMetrics, _snapshot


async def retrieve_jsearch_market(goal, client, *, limits=None, now=None):
    bounded = limits or SearchLimits()
    plan = build_search_plan(goal)
    if plan.status is not SearchPlanStatus.READY:
        return MarketRetrievalResult(plan=plan)
    timestamp = now or datetime.now(UTC)
    scope = plan.allowed_geography_scopes[0]
    metrics = _RunMetrics()
    evidence, audits, seen_ids = [], [], set()
    details_attempted = details_succeeded = 0
    query = f"{plan.search_title} in {plan.geography.lower()}"
    request = StructuredJobSearchRequest(
        title=plan.search_title,
        location=plan.geography,
        country=client.country,
        geography_scope=scope,
    )
    detail_budget = min(client.max_details, bounded.max_content_fetches)
    quota_stopped = False
    async with client:
        metrics.search_attempts = 1
        page = await client.search_page(request)
        metrics.search_successes = 1
        metrics.exact_search_queries = [query]
        raw_count = (
            page.input_result_count if page.input_result_count is not None else len(page.results)
        )
        metrics.exact_raw_result_count = raw_count
        metrics.malformed_response_count = page.malformed_result_count
        metrics.budget_deferred_results = page.deferred_result_count
        if page.continuation_available:
            metrics.limitations.append(
                "JSearch indicates more results; pagination was not requested."
            )
        if page.malformed_result_count:
            metrics.limitations.append(
                f"{page.malformed_result_count} results could not be normalized; "
                "see normalization issues."
            )
        # Identity dedup happens before detail calls, so duplicates do not spend quota.
        for raw in page.results:
            audit = dict(
                provider=MarketSourceProvider.JSEARCH,
                source_url=raw.url,
                source_type=PostingSourceType.STRUCTURED_JOB,
                title=raw.title,
                employer=raw.company,
                location=raw.location,
                parent_result_id=raw.provider_job_id,
                input_description_characters=len(raw.description),
            )
            if raw.provider_job_id in seen_ids:
                metrics.duplicate_count += 1
                audits.append(
                    PostingRetrievalAudit(
                        **audit,
                        rejection_reason="Duplicate JSearch job ID",
                        routing_decision="DUPLICATE",
                    )
                )
                continue
            seen_ids.add(raw.provider_job_id)
            status = EnrichmentStatus.NOT_NEEDED
            notes = []
            if raw.description_origin == "SEARCH_HIGHLIGHTS" or description_incomplete(
                raw.description
            ):
                status = EnrichmentStatus.NOT_ATTEMPTED
                if details_attempted < detail_budget and not quota_stopped:
                    details_attempted += 1
                    try:
                        detail = await client.job_details(
                            raw.provider_job_id, country=client.country
                        )
                        if (
                            detail
                            and detail.provider_job_id == raw.provider_job_id
                            and detail.description
                            and (
                                len(detail.description) > len(raw.description)
                                or (
                                    detail.description_origin == "SEARCH_DESCRIPTION"
                                    and not description_incomplete(detail.description)
                                )
                            )
                        ):
                            # Keep discovery identity; details must match the requested job ID.
                            raw = raw.model_copy(
                                update={
                                    "description": detail.description,
                                    "content_complete": detail.content_complete,
                                    "description_origin": "JOB_DETAILS_HIGHLIGHTS"
                                    if detail.description_origin.endswith("HIGHLIGHTS")
                                    else "JOB_DETAILS",
                                }
                            )
                            details_succeeded += 1
                            status = EnrichmentStatus.APPLIED
                        else:
                            status = EnrichmentStatus.FAILED
                            notes.append(
                                "Matching Job Details did not supply an improved description."
                            )
                    except (MarketAuthenticationError, MarketRateLimitError):
                        quota_stopped = True
                        status = EnrichmentStatus.FAILED
                        metrics.limitations.append(
                            "JSearch details stopped: check subscription/quota."
                        )
                        notes.append(
                            "Details request failed: subscription or quota check required."
                        )
                    except MarketIntelligenceError:
                        status = EnrichmentStatus.FAILED
                        metrics.content_failure_count += 1
                        notes.append("Details request failed; original search content preserved.")
                else:
                    metrics.budget_deferred_results += 1
                    notes.append(
                        "Details not attempted: quota/authentication stop."
                        if quota_stopped
                        else "Details not attempted: request budget reached."
                    )
            if raw.description_origin.endswith("HIGHLIGHTS"):
                notes.append(
                    "Only supplied Responsibilities/Qualifications highlights are available; "
                    "not a full description."
                )
            if description_incomplete(raw.description):
                notes.append(
                    "Description remains missing or visibly truncated; "
                    "this is not a candidate skill gap."
                )
            observation = {
                "description_origin": raw.description_origin,
                "provider_stable_id": raw.provider_stable_id,
                "publisher": raw.publisher,
                "reported_location": raw.reported_location,
                "is_remote": raw.is_remote,
                "application_is_direct": raw.application_is_direct,
            }
            audit.update(routing_notes=notes, enrichment_observation=observation)
            try:
                item = _primary_evidence(
                    raw,
                    goal_geography=plan.geography,
                    requested_scope=scope,
                    retrieved_at=timestamp,
                    thin_description_characters=bounded.thin_description_characters,
                    target_role=plan.search_title,
                    target_seniority=plan.target_seniority,
                )
            except ValueError:
                metrics.rejected_candidates += 1
                audits.append(
                    PostingRetrievalAudit(
                        **audit,
                        rejection_reason="Invalid posting metadata or dates",
                        enrichment_status=status,
                        routing_decision="INVALID_METADATA",
                    )
                )
                continue
            reason = None
            rejected_route = "CURRENTNESS_EXCLUDED"
            if item is None:
                reason = "Location out of scope/unclear, or invalid posting URL"
                rejected_route = "LOCATION_OR_POSTING_REVIEW"
                metrics.geography_out_of_scope_count += 1
            else:
                reason = currentness_rejection(
                    item.primary_content,
                    as_of=timestamp.date(),
                    max_age_days=bounded.max_posting_age_days,
                )
            if reason:
                metrics.rejected_candidates += 1
                audits.append(
                    PostingRetrievalAudit(
                        **audit,
                        rejection_reason=reason,
                        enrichment_status=status,
                        routing_decision=rejected_route,
                    )
                )
                continue
            if item.title_classification not in {
                PostingTitleMatch.EXACT_TARGET,
                PostingTitleMatch.TARGET_VARIANT,
                PostingTitleMatch.RELATED_TITLE,
            }:
                # Discovery is broader than the target-market cohort. Preserve the
                # result in the audit, but never feed unrelated jobs into analysis.
                metrics.rejected_candidates += 1
                audits.append(
                    PostingRetrievalAudit(
                        **audit,
                        posting_id=str(item.posting.posting_id),
                        title_classification=item.title_classification,
                        seniority_classification=item.seniority_classification,
                        content_quality=item.content_quality,
                        rejection_reason=(
                            "Outside target-role cohort: unrelated role classification"
                        ),
                        enrichment_status=status,
                        routing_decision="ROLE_RELEVANCE_REVIEW",
                    )
                )
                continue
            duplicate = next(
                (prior for prior in evidence if same_vacancy(prior.posting, item.posting)), None
            )
            if duplicate:
                metrics.duplicate_count += 1
                audits.append(
                    PostingRetrievalAudit(
                        **audit,
                        duplicate_of=str(duplicate.posting.posting_id),
                        rejection_reason="Same verified posting identity",
                        enrichment_status=status,
                        routing_decision="DUPLICATE",
                    )
                )
                continue
            item = item.model_copy(
                update={
                    "enrichment_status": status,
                    "enrichment_observation": observation,
                    "limitations": list(dict.fromkeys([*item.limitations, *notes])),
                }
            )
            evidence.append(item)
            audits.append(
                PostingRetrievalAudit(
                    **audit,
                    posting_id=str(item.posting.posting_id),
                    title_classification=item.title_classification,
                    seniority_classification=item.seniority_classification,
                    selected_content_source=MarketSourceProvider.JSEARCH,
                    selected_for_primary_evidence=True,
                    content_quality=item.content_quality,
                    enrichment_status=status,
                    routing_decision=(
                        "RETAINED_MISSING_DESCRIPTION"
                        if not raw.description.strip()
                        else "RETAINED_LIMITED_CONTENT"
                        if raw.description_origin.endswith("HIGHLIGHTS")
                        or description_incomplete(raw.description)
                        else "RETAINED_DESCRIPTION"
                    ),
                )
            )
    metrics.limitations.extend(
        [
            "One bounded JSearch search, not a complete market count or verified vacancy list.",
            "Descriptions are supplied by JSearch; completeness is not independently verified.",
        ]
    )
    if any(description_incomplete(item.primary_content.markdown) for item in evidence):
        metrics.limitations.append(
            "Some descriptions remain missing or truncated after bounded details."
        )
    sources = [item.primary_source for item in evidence]
    postings = [item.posting for item in evidence]
    snapshot = _snapshot(
        plan=plan,
        postings=postings,
        sources=sources,
        metrics=metrics,
        search_date=timestamp.date(),
        title_classifications={
            item.posting.posting_id: PostingTitleMatch(item.title_classification)
            for item in evidence
        },
    )
    return MarketRetrievalResult(
        plan=plan,
        snapshot=snapshot,
        sources=sources,
        postings=postings,
        posting_evidence=evidence,
        source_contents=[
            RetainedSourceContent(source=item.primary_source, content=item.primary_content)
            for item in evidence
        ],
        primary_provider=MarketSourceProvider.JSEARCH,
        primary_search_count=1,
        raw_source_count=raw_count,
        exact_raw_result_count=raw_count,
        exact_search_queries=[query],
        total_unique_retained_posting_count=len(evidence),
        exact_title_validated_count=snapshot.exact_title_count,
        target_variant_validated_count=snapshot.target_variant_count,
        related_title_validated_count=snapshot.related_title_count,
        enrichment_attempt_count=details_attempted,
        enrichment_success_count=details_succeeded,
        rejected_result_count=page.malformed_result_count + metrics.rejected_candidates,
        posting_audits=audits,
        normalization_issues=page.normalization_issues,
        continuation_available=page.continuation_available,
        provider_request_id=page.response_request_id,
        source_coverage_confidence=ConfidenceLevel.LOW,
        source_coverage_reason="JSearch-only retrieval; no independent source cross-check.",
        budget_deferred_result_count=metrics.budget_deferred_results,
        effective_budgets={
            "jsearch_search_calls": 1,
            "jsearch_detail_calls": detail_budget,
            "automatic_retries": 0,
        },
    )
