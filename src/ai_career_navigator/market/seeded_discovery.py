"""Find missing vacancy bodies using structured discovery as a search seed.

A seed guides the search, never supplies missing identity fields to another job.
All returned pages pass the same untrusted-content validation as independent search.
"""

from datetime import datetime

from ai_career_navigator.market.mcp.protocol import MarketSearchClient
from ai_career_navigator.market.normalization import normalize_whitespace
from ai_career_navigator.market.schemas import (
    MarketPostingEvidence,
    MarketRetrievalResult,
    MarketSearchRequest,
    MarketSourceProvider,
    SearchFreshness,
    SearchLimits,
    SearchPassReport,
    SearchPassType,
    SearchPlan,
)
from ai_career_navigator.market.service import _retrieve_candidates, _RunMetrics, _search


def seed_request(seed: MarketPostingEvidence, plan: SearchPlan) -> MarketSearchRequest:
    def phrase(value: str | None) -> str:
        # Keep all role-defining words; do not introduce role-specific substitutions.
        return normalize_whitespace((value or "").replace('"', " "))

    employer = phrase(seed.posting.employer)
    query = " ".join(
        part
        for part in (
            f'"{employer}"' if employer else "",
            phrase(seed.posting.original_title),
            phrase(seed.posting.grounded_location or seed.posting.location or plan.geography),
            '(careers OR jobs OR "job description")',
        )
        if part
    )
    return MarketSearchRequest(
        query=query,
        pass_type=SearchPassType.POSTING_ENRICHMENT,
        freshness=SearchFreshness.YEAR,
        count=3,
        geography_scope=seed.posting.requested_geography_scope or plan.allowed_geography_scopes[0],
        full_page=True,
        crawl_timeout_seconds=60,
    )


async def discover_from_seed(
    seed: MarketPostingEvidence,
    *,
    client: MarketSearchClient,
    plan: SearchPlan,
    limits: SearchLimits,
    metrics: _RunMetrics,
    seen_urls: set[str],
    timestamp: datetime,
) -> MarketRetrievalResult:
    request = seed_request(seed, plan)
    candidates = await _search(client, request, metrics, limits)
    sources, contents, postings = [], [], []
    start = len(metrics.posting_audits)
    rejected_before = metrics.rejected_results
    direct_before = metrics.direct_page_count
    aggregator_before = metrics.aggregator_result_count
    await _retrieve_candidates(
        client=client,
        candidates=candidates,
        plan=plan,
        limits=limits,
        metrics=metrics,
        seen_urls=seen_urls,
        sources=sources,
        source_contents=contents,
        postings=postings,
        retrieval_date=timestamp.date(),
        retrieved_at=timestamp,
        requested_geography_scope=request.geography_scope,
        provider=MarketSourceProvider.YOU,
        individual_postings_only=True,
        candidate_result_cap=request.count,
    )
    metrics.search_passes.append(
        SearchPassReport(
            provider=MarketSourceProvider.YOU,
            pass_type=request.pass_type,
            freshness=request.freshness,
            query=request.query,
            request_parameters=request.model_dump(mode="json"),
            raw_result_count=len(candidates),
            validated_posting_count=len(postings),
            aggregator_result_count=metrics.aggregator_result_count - aggregator_before,
            direct_page_count=metrics.direct_page_count - direct_before,
            geography_scope=request.geography_scope,
            geography_valid_posting_count=len(postings),
        )
    )
    return MarketRetrievalResult(
        plan=plan,
        sources=sources,
        source_contents=contents,
        postings=postings,
        posting_audits=metrics.posting_audits[start:],
        rejected_result_count=metrics.rejected_results - rejected_before,
        you_context_result_count=sum(
            audit.source_type.value in {"BACKGROUND_CONTEXT", "AGGREGATOR_PAGE"}
            for audit in metrics.posting_audits[start:]
        ),
    )
