"""Run one explicitly bounded live market-retrieval and requirement-extraction slice."""

import argparse
import asyncio
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import Any, Self

from ai_career_navigator.config import Settings
from ai_career_navigator.domain import (
    ApprovalStatus,
    CareerGoal,
    GeographyScope,
    GoalType,
)
from ai_career_navigator.market import (
    SearchLimits,
    analyze_market_requirements,
    retrieve_current_market,
)
from ai_career_navigator.market.mcp import YouMcpMarketSearchClient
from ai_career_navigator.market.schemas import (
    MarketPageContent,
    MarketSearchRequest,
    MarketSearchResult,
    SearchPassType,
)
from ai_career_navigator.models import ModelGateway, ModelRole
from ai_career_navigator.models.protocols import ModelProvider
from ai_career_navigator.models.providers import configured_provider
from ai_career_navigator.models.schemas import ModelRequest, ModelResponse


@dataclass
class MarketUsage:
    search_calls: int = 0
    search_results: int = 0
    content_calls: int = 0
    search_failures: list[str] = field(default_factory=list)
    content_failures: list[str] = field(default_factory=list)
    queries: list[str] = field(default_factory=list)


class TrackedMarketClient:
    """Count safe market operations while preserving the production adapter boundary."""

    def __init__(self, client: YouMcpMarketSearchClient) -> None:
        self._client = client
        self.usage = MarketUsage()

    async def __aenter__(self) -> Self:
        await self._client.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self._client.__aexit__(exc_type, exc_value, traceback)

    async def search(self, request: MarketSearchRequest) -> list[MarketSearchResult]:
        self.usage.search_calls += 1
        self.usage.queries.append(request.query)
        try:
            results = await self._client.search(request)
        except Exception as error:
            self.usage.search_failures.append(type(error).__name__)
            raise
        self.usage.search_results += len(results)
        return results

    async def fetch_content(self, url: str) -> MarketPageContent:
        self.usage.content_calls += 1
        try:
            return await self._client.fetch_content(url)
        except Exception as error:
            self.usage.content_failures.append(type(error).__name__)
            raise


@dataclass
class ModelUsage:
    calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    unknown_input_token_calls: int = 0
    unknown_output_token_calls: int = 0
    failures: list[str] = field(default_factory=list)


class TrackedModelProvider:
    """Collect normalized usage without retaining prompts, content, or credentials."""

    def __init__(self, provider: ModelProvider) -> None:
        self._provider = provider
        self.usage = ModelUsage()

    @property
    def provider_name(self) -> str:
        return self._provider.provider_name

    def _record(self, response: ModelResponse) -> ModelResponse:
        self.usage.successful_calls += 1
        if response.input_tokens is None:
            self.usage.unknown_input_token_calls += 1
        else:
            self.usage.input_tokens += response.input_tokens
        if response.output_tokens is None:
            self.usage.unknown_output_token_calls += 1
        else:
            self.usage.output_tokens += response.output_tokens
        return response

    def _failed(self, error: Exception) -> None:
        self.usage.failed_calls += 1
        self.usage.failures.append(type(error).__name__)

    def generate_text(
        self, *, request: ModelRequest, model: str, timeout_seconds: float
    ) -> ModelResponse:
        self.usage.calls += 1
        try:
            response = self._provider.generate_text(
                request=request, model=model, timeout_seconds=timeout_seconds
            )
        except Exception as error:
            self._failed(error)
            raise
        return self._record(response)

    def generate_structured(
        self,
        *,
        request: ModelRequest,
        model: str,
        output_schema: dict[str, Any],
        timeout_seconds: float,
    ) -> ModelResponse:
        self.usage.calls += 1
        try:
            response = self._provider.generate_structured(
                request=request,
                model=model,
                output_schema=output_schema,
                timeout_seconds=timeout_seconds,
            )
        except Exception as error:
            self._failed(error)
            raise
        return self._record(response)


def _settings(env_file: Path) -> Settings:
    if not env_file.is_file():
        raise SystemExit(f"Environment file not found: {env_file}")
    settings = Settings(_env_file=env_file)
    if settings.llm_provider != "nvidia":
        raise SystemExit("This validation requires LLM_PROVIDER=nvidia.")
    if settings.nvidia_api_key is None:
        raise SystemExit("NVIDIA_API_KEY is required; its value will not be printed.")
    if settings.ydc_api_key is None:
        raise SystemExit("YDC_API_KEY is required; its value will not be printed.")
    return settings


async def _run(settings: Settings, *, posting_limit: int) -> dict[str, object]:
    goal = CareerGoal(
        goal_type=GoalType.TARGET_CAREER_PATH,
        target_role="AI Solutions Architect",
        target_location="Canada",
        geography_scopes=[GeographyScope.COUNTRY],
        search_expansion_permission=True,
        approval_status=ApprovalStatus.APPROVED,
        approved_at=datetime.now(UTC),
    )
    market_client = TrackedMarketClient(YouMcpMarketSearchClient.from_settings(settings))
    retrieval = await retrieve_current_market(
        goal,
        market_client,
        limits=SearchLimits(
            max_search_queries=min(3, settings.market_max_search_queries),
            max_expansion_queries=settings.market_max_expansion_queries,
            max_content_fetches=12,
            target_posting_count=posting_limit,
            expansion_threshold=posting_limit,
            max_retries=0,
            discovery_result_count=settings.market_discovery_result_count,
            direct_source_excluded_domains=settings.market_direct_excluded_domains,
        ),
    )
    snapshot = retrieval.snapshot
    if snapshot is None:
        raise RuntimeError("Market retrieval did not produce a snapshot.")

    source_references = {str(source.source_id): source.title for source in retrieval.sources}
    retrieved_postings = [
        {
            "title": posting.original_title,
            "employer": posting.employer or "Unknown employer",
            "location": posting.location or "Unknown location",
            "requested_scope": (
                posting.requested_geography_scope.value
                if posting.requested_geography_scope is not None
                else "Unavailable"
            ),
            "matched_scope": (
                posting.matched_geography_scope.value
                if posting.matched_geography_scope is not None
                else "Unavailable"
            ),
            "grounded_location": posting.grounded_location or "Unavailable",
            "location_evidence": posting.location_evidence_text or "Unavailable",
            "source_reference": source_references.get(str(posting.source_id), "Unknown source"),
        }
        for posting in retrieval.postings
    ]
    direct_passes = [
        item for item in retrieval.search_passes if item.pass_type is SearchPassType.DIRECT_SOURCE
    ]
    general_passes = [
        item for item in retrieval.search_passes if item.pass_type is SearchPassType.GENERAL_WEB
    ]
    related_passes = [
        item for item in retrieval.search_passes if item.pass_type is SearchPassType.RELATED_TITLE
    ]
    target_variant_passes = [
        item for item in retrieval.search_passes if item.pass_type is SearchPassType.TARGET_VARIANT
    ]
    pass_reports = [
        {
            "pass_type": item.pass_type.value,
            "freshness": item.freshness.value,
            "query": item.query,
            "raw_results": item.raw_result_count,
            "validated_postings": item.validated_posting_count,
            "aggregator_results": item.aggregator_result_count,
            "direct_pages": item.direct_page_count,
            "requested_geography_scope": item.geography_scope.value,
            "geography_valid_postings": item.geography_valid_posting_count,
        }
        for item in retrieval.search_passes
    ]
    geography_scope_funnel = {
        scope.value: {
            "allowed": scope in retrieval.plan.allowed_geography_scopes,
            "query_count": sum(item.geography_scope is scope for item in retrieval.search_passes),
            "raw_results": sum(
                item.raw_result_count
                for item in retrieval.search_passes
                if item.geography_scope is scope
            ),
            "geography_valid_postings": retrieval.geography_valid_postings_by_scope.get(scope, 0),
        }
        for scope in GeographyScope
    }
    report: dict[str, object] = {
        "scope": {
            "target_role": goal.target_role,
            "geography": goal.target_location,
            "allowed_geography_scopes": [
                scope.value for scope in retrieval.plan.allowed_geography_scopes
            ],
            "posting_cap": posting_limit,
            "full_twenty_target_used": False,
        },
        "retrieval_funnel": {
            "search_passes": pass_reports,
            "direct_source": {
                "query_count": len(direct_passes),
                "raw_results": sum(item.raw_result_count for item in direct_passes),
                "validated_postings": sum(item.validated_posting_count for item in direct_passes),
            },
            "general_web": {
                "query_count": len(general_passes),
                "raw_results": sum(item.raw_result_count for item in general_passes),
                "validated_postings": sum(item.validated_posting_count for item in general_passes),
            },
            "target_variant": {
                "query_count": len(target_variant_passes),
                "raw_results": sum(item.raw_result_count for item in target_variant_passes),
                "validated_postings": retrieval.target_variant_validated_count,
            },
            "related_title": {
                "query_count": len(related_passes),
                "raw_results": sum(item.raw_result_count for item in related_passes),
                "validated_postings": sum(item.validated_posting_count for item in related_passes),
            },
            "freshness_fallback_used": retrieval.freshness_fallback_used,
            "aggregator_results_encountered": retrieval.aggregator_result_count,
            "direct_pages_encountered": retrieval.direct_page_count,
            "raw_source_count": retrieval.raw_source_count,
            "segmented_candidate_count": retrieval.segmented_candidate_count,
            "title_grounded_candidate_count": retrieval.title_grounded_candidate_count,
            "geography_valid_candidate_count": retrieval.geography_valid_candidate_count,
            "geography_valid_postings_by_scope": {
                scope.value: retrieval.geography_valid_postings_by_scope.get(scope, 0)
                for scope in GeographyScope
            },
            "geography_scope_funnel": geography_scope_funnel,
            "exact_search_queries": retrieval.exact_search_queries,
            "exact_raw_results": retrieval.exact_raw_result_count,
            "exact_title_validated_count": retrieval.exact_title_validated_count,
            "target_variant_search_queries": retrieval.target_variant_search_queries,
            "target_variant_raw_results": retrieval.target_variant_raw_result_count,
            "target_variant_validated_count": retrieval.target_variant_validated_count,
            "expansion_triggered": retrieval.expansion_triggered,
            "expansion_titles": retrieval.expansion_titles,
            "related_search_queries": retrieval.related_search_queries,
            "related_raw_results": retrieval.related_raw_result_count,
            "related_title_validated_count": retrieval.related_title_validated_count,
            "geography_out_of_scope_count": retrieval.geography_out_of_scope_count,
            "geography_unclear_count": retrieval.geography_unclear_count,
            "rejected_url_like_title_count": retrieval.rejected_url_like_title_count,
            "total_unique_retained_postings": (retrieval.total_unique_retained_posting_count),
            "content_fetch_attempts": snapshot.content_fetch_count,
            "content_fetch_successes": snapshot.successful_content_fetch_count,
            "rejected_results": retrieval.rejected_result_count,
            "duplicate_postings": snapshot.duplicate_posting_count,
        },
        "retrieval_counts": {
            "exact": snapshot.exact_title_count,
            "target_variant": snapshot.target_variant_count,
            "related": snapshot.related_title_count,
            "distinct_employers": snapshot.distinct_employer_count,
        },
        "employers": sorted(
            {posting.employer or "Unknown employer" for posting in retrieval.postings},
            key=str.casefold,
        ),
        "postings": retrieved_postings,
        "failures": {
            "market_search": market_client.usage.search_failures,
            "market_content": market_client.usage.content_failures,
            "model": [],
        },
        "limitations": list(snapshot.limitations),
        "usage": {
            "you_search_calls": market_client.usage.search_calls,
            "you_content_calls": market_client.usage.content_calls,
            "nvidia_calls": 0,
            "nvidia_successful_calls": 0,
            "nvidia_failed_calls": 0,
            "nvidia_input_tokens": 0,
            "nvidia_output_tokens": 0,
            "unknown_input_token_calls": 0,
            "unknown_output_token_calls": 0,
        },
    }
    target_evidence_count = snapshot.exact_title_count + snapshot.target_variant_count
    if target_evidence_count < 3:
        report["extraction_counts"] = {
            "status": "SKIPPED_INSUFFICIENT_VALIDATED_POSTINGS",
            "minimum_required": 3,
            "available": target_evidence_count,
        }
        report["requirements"] = []
        report["stop_point"] = "QA_BEFORE_REQUIREMENT_EXTRACTION"
        return report

    retained_source_ids = {posting.source_id for posting in retrieval.postings}
    extraction_sources = [
        item for item in retrieval.source_contents if item.source.source_id in retained_source_ids
    ]
    model_provider = TrackedModelProvider(configured_provider(settings))
    gateway = ModelGateway(
        provider=model_provider,
        models={
            ModelRole.EXTRACTION: settings.extraction_model,
            ModelRole.REASONING: settings.reasoning_model,
            ModelRole.VALIDATION: settings.validation_model,
        },
        timeout_seconds=settings.model_timeout_seconds,
        max_retries=0,
    )
    analysis = analyze_market_requirements(
        extraction_sources,
        target_role=goal.target_role or "",
        geography=goal.target_location or "Location not specified",
        model_gateway=gateway,
        allow_related_titles=False,
        posting_limit=posting_limit,
    )
    employers = sorted(
        {posting.employer or "Unknown employer" for posting in analysis.postings},
        key=str.casefold,
    )
    posting_titles = [
        {
            "title": posting.original_title,
            "employer": posting.employer or "Unknown employer",
            "location": posting.location or "Unknown location",
        }
        for posting in analysis.postings
    ]
    requirements = [
        {
            "capability": item.normalized_capability or item.requirement_text,
            "category": item.category.value,
            "mandatory": item.mandatory,
            "preferred": item.preferred,
            "years_required": item.years_required,
            "maturity_expected": (
                item.maturity_expected.value if item.maturity_expected is not None else None
            ),
            "confidence": item.extraction_confidence.value,
            "sample_frequency": item.frequency_within_sample,
        }
        for item in analysis.requirements
    ]
    report["extraction_counts"] = {
        "source_pages": analysis.summary.source_page_count,
        "identified_candidates": analysis.summary.identified_candidate_count,
        "validated_in_scope": analysis.summary.validated_in_scope_posting_count,
        "analyzed": analysis.summary.analyzed_posting_count,
        "exact": analysis.summary.exact_title_analyzed_count,
        "target_variant": analysis.summary.target_variant_analyzed_count,
        "related": analysis.summary.related_title_analyzed_count,
        "requirements": len(analysis.requirements),
        "status": analysis.status.value,
    }
    report["employers"] = employers
    report["postings"] = posting_titles
    report["requirements"] = requirements
    report["failures"] = {
        "market_search": market_client.usage.search_failures,
        "market_content": market_client.usage.content_failures,
        "model": model_provider.usage.failures,
    }
    report["limitations"] = list(
        dict.fromkeys([*snapshot.limitations, *analysis.summary.limitations])
    )
    report["usage"] = {
        "you_search_calls": market_client.usage.search_calls,
        "you_content_calls": market_client.usage.content_calls,
        "nvidia_calls": model_provider.usage.calls,
        "nvidia_successful_calls": model_provider.usage.successful_calls,
        "nvidia_failed_calls": model_provider.usage.failed_calls,
        "nvidia_input_tokens": model_provider.usage.input_tokens,
        "nvidia_output_tokens": model_provider.usage.output_tokens,
        "unknown_input_token_calls": model_provider.usage.unknown_input_token_calls,
        "unknown_output_token_calls": model_provider.usage.unknown_output_token_calls,
    }
    report["stop_point"] = "QA_BEFORE_CANDIDATE_COMPARISON"
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--posting-limit", type=int, choices=range(3, 6), default=5)
    args = parser.parse_args()
    settings = _settings(args.env_file)
    report = asyncio.run(_run(settings, posting_limit=args.posting_limit))
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
