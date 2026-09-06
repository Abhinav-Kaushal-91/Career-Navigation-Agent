"""Manual bounded Adzuna -> optional You -> NVIDIA validation slice."""

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from live_validate_market_slice import TrackedModelProvider

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
    build_enrichment_market_client,
    build_primary_market_client,
    retrieve_combined_market,
)
from ai_career_navigator.models import ModelGateway, ModelRole
from ai_career_navigator.models.providers import configured_provider


def _settings(path: Path) -> Settings:
    if not path.is_file():
        raise SystemExit(f"Environment file not found: {path}")
    settings = Settings(_env_file=path)
    missing = []
    if settings.adzuna_app_id is None or settings.adzuna_app_key is None:
        missing.append("Adzuna credentials")
    if settings.ydc_api_key is None:
        missing.append("YDC_API_KEY")
    if settings.nvidia_api_key is None or settings.llm_provider != "nvidia":
        missing.append("NVIDIA provider configuration")
    if missing:
        raise SystemExit(f"Missing configuration: {', '.join(missing)}. Values are not printed.")
    return settings


async def _run(settings: Settings, posting_limit: int) -> dict[str, object]:
    goal = CareerGoal(
        goal_type=GoalType.TARGET_CAREER_PATH,
        target_role="AI Solutions Architect",
        target_location="Canada",
        geography_scopes=[GeographyScope.COUNTRY],
        search_expansion_permission=True,
        approval_status=ApprovalStatus.APPROVED,
        approved_at=datetime.now(UTC),
    )
    retrieval = await retrieve_combined_market(
        goal,
        build_primary_market_client(settings),
        enrichment_client=build_enrichment_market_client(settings),
        limits=SearchLimits(
            max_search_queries=1,
            max_variant_queries=4,
            max_expansion_queries=0,
            max_content_fetches=12,
            target_posting_count=posting_limit,
            discovery_result_count=settings.market_discovery_result_count,
            max_retries=0,
        ),
        max_pages=2,
        max_enrichments=2,
    )
    snapshot = retrieval.snapshot
    assert snapshot is not None
    report: dict[str, object] = {
        "stop_point": "QA_BEFORE_CANDIDATE_COMPARISON",
        "providers": {
            "structured_discovery": "adzuna",
            "web_discovery": "you",
            "parallel_discovery": retrieval.parallel_discovery,
            "extraction": "nvidia",
            "degraded_discovery": retrieval.degraded_discovery,
            "source_coverage_confidence": retrieval.source_coverage_confidence.value,
            "source_coverage_reason": retrieval.source_coverage_reason,
        },
        "retrieval": {
            "adzuna_search_calls": retrieval.primary_search_count,
            "you_search_calls": retrieval.you_search_count,
            "adzuna_validated": retrieval.adzuna_validated_count,
            "you_validated": retrieval.you_validated_count,
            "cross_source_matches": retrieval.cross_source_match_count,
            "validated_postings": snapshot.validated_posting_count,
            "exact": snapshot.exact_title_count,
            "target_variants": snapshot.target_variant_count,
            "related": snapshot.related_title_count,
            "duplicates": snapshot.duplicate_posting_count,
            "enrichment_attempts": retrieval.enrichment_attempt_count,
            "enrichment_successes": retrieval.enrichment_success_count,
        },
        "postings": [
            {
                "title": item.original_title,
                "employer": item.employer or "unknown",
                "location": item.location or "unknown",
            }
            for item in retrieval.postings
        ],
        "limitations": snapshot.limitations,
        "nvidia_calls": 0,
        "capability_requirements": [],
        "prerequisite_conditions": [],
    }
    if len(retrieval.posting_evidence) < 3:
        report["stop_point"] = "QA_BEFORE_REQUIREMENT_EXTRACTION"
        return report
    tracked_provider = TrackedModelProvider(configured_provider(settings))
    gateway = ModelGateway(
        provider=tracked_provider,
        models={
            ModelRole.EXTRACTION: settings.extraction_model,
            ModelRole.REASONING: settings.reasoning_model,
            ModelRole.VALIDATION: settings.validation_model,
        },
        timeout_seconds=settings.model_timeout_seconds,
        max_retries=1,
    )
    analysis = analyze_market_requirements(
        retrieval.posting_evidence,
        target_role=goal.target_role or "",
        geography=goal.target_location or "Canada",
        model_gateway=gateway,
        allow_related_titles=True,
        posting_limit=posting_limit,
    )
    report["nvidia_calls"] = tracked_provider.usage.calls
    report["nvidia_input_tokens"] = tracked_provider.usage.input_tokens
    report["nvidia_output_tokens"] = tracked_provider.usage.output_tokens
    report["nvidia_failed_calls"] = tracked_provider.usage.failed_calls
    report["extraction"] = {
        "selected_postings": analysis.summary.validated_in_scope_posting_count,
        "analyzed_postings": analysis.summary.analyzed_posting_count,
        "exact": analysis.summary.exact_title_analyzed_count,
        "target_variants": analysis.summary.target_variant_analyzed_count,
        "related": analysis.summary.related_title_analyzed_count,
        "capabilities_extracted": sum(
            item.accepted_capability_requirement_count for item in analysis.summary.posting_quality
        ),
        "prerequisites_extracted": sum(
            item.prerequisite_condition_count for item in analysis.summary.posting_quality
        ),
        "metadata_items_rejected": sum(
            item.rejected_metadata_non_requirement_count
            for item in analysis.summary.posting_quality
        ),
        "extraction_failures": (
            analysis.summary.validated_in_scope_posting_count
            - analysis.summary.analyzed_posting_count
        ),
    }
    report["candidate_comparison_gate"] = (
        "PASS" if analysis.summary.analyzed_posting_count >= 4 else "STOP"
    )
    prerequisite_categories = {
        "EDUCATION",
        "CREDENTIAL",
        "LOCATION",
        "WORK_AUTHORIZATION",
        "LANGUAGE",
    }
    report["capability_requirements"] = [
        {
            "capability": item.normalized_capability or item.requirement_text,
            "mandatory": item.mandatory,
            "preferred": item.preferred,
            "confidence": item.extraction_confidence.value,
        }
        for item in analysis.requirements
        if item.category.value not in prerequisite_categories
    ]
    report["prerequisite_conditions"] = [
        {
            "condition": item.normalized_capability or item.requirement_text,
            "mandatory": item.mandatory,
            "preferred": item.preferred,
            "confidence": item.extraction_confidence.value,
        }
        for item in analysis.requirements
        if item.category.value in prerequisite_categories
    ]
    report["requirements_per_posting"] = {
        str(posting.posting_id): [
            item.normalized_capability or item.requirement_text
            for item in analysis.requirements
            if item.posting_id == posting.posting_id
        ]
        for posting in analysis.postings
    }

    def aggregates(items):  # type: ignore[no-untyped-def]
        return [
            {
                "capability": item.normalized_capability,
                "exact_frequency": item.exact_title_frequency,
                "exact_and_variant_frequency": item.exact_and_variant_frequency,
                "combined_frequency": item.combined_frequency,
                "observed": (
                    f"{len(item.requirement_ids)} "
                    f"of {analysis.summary.analyzed_posting_count} analyzed postings"
                ),
            }
            for item in items
        ]

    report["aggregate_capability_requirements"] = aggregates(
        analysis.summary.capability_requirements
    )
    report["aggregate_prerequisite_conditions"] = aggregates(
        analysis.summary.prerequisite_requirements
    )
    report["posting_extraction_qa"] = [
        {
            "title": item.title,
            "employer": item.employer or "unknown",
            "input_description_characters": item.input_description_characters,
            "enrichment_used": item.enrichment_used,
            "raw_extracted_items": item.raw_extracted_item_count,
            "accepted_capabilities": item.accepted_capability_requirement_count,
            "prerequisites": item.prerequisite_condition_count,
            "rejected_metadata_or_non_requirements": (item.rejected_metadata_non_requirement_count),
            "unsupported_grounding_groups": item.unsupported_grounding_count,
            "failure_category": item.failure_category,
            "limitations": item.limitations,
        }
        for item in analysis.summary.posting_quality
    ]
    report["limitations"] = list(
        dict.fromkeys([*snapshot.limitations, *analysis.summary.limitations])
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--posting-limit", type=int, choices=range(3, 6), default=5)
    args = parser.parse_args()
    print(json.dumps(asyncio.run(_run(_settings(args.env_file), args.posting_limit)), indent=2))


if __name__ == "__main__":
    main()
