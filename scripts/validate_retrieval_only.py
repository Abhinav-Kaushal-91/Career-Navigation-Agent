"""Bounded public-job retrieval check. No candidate profile or model calls.

Requires --allow-live; writes a new local, sanitized diagnostic artifact, never
overwrites an earlier run. Uses the same retrieval service/clients as the portal.
"""

import argparse
import asyncio
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from pydantic import SecretStr

from ai_career_navigator.config import Settings
from ai_career_navigator.domain import ApprovalStatus, CareerGoal, GeographyScope, GoalType
from ai_career_navigator.market import (
    SearchLimits,
    build_enrichment_market_client,
    build_primary_market_client,
    retrieve_combined_market,
)
from ai_career_navigator.market.errors import MarketIntelligenceError
from ai_career_navigator.models.inspection import LocalModelInspector


async def run_retrieval(settings, *, role, location, primary=None, support=None):
    settings = settings.model_copy(
        update={
            "market_timeout_seconds": min(25.0, settings.market_timeout_seconds),
            "max_retries": 0,
            "langsmith_tracing": False,
        }
    )
    limits = SearchLimits(
        max_total_search_calls=6,
        max_search_queries=3,
        max_content_fetches=12,
        max_variant_queries=2,
        max_expansion_queries=0,
        analysis_posting_limit=5,
        max_enrichments=5,
        target_posting_count=10,
        max_retries=0,
    )
    goal = CareerGoal(
        goal_type=GoalType.CURRENT_MARKET_ANALYSIS,
        target_role=role,
        target_location=location,
        geography_scopes=[GeographyScope.STRICT_CITY],
        search_expansion_permission=False,
        approval_status=ApprovalStatus.APPROVED,
        approved_at=datetime.now(UTC),
    )
    report = {
        "mode": "LIVE_RETRIEVAL_ONLY",
        "started_at": datetime.now(UTC).isoformat(),
        "target_role": role,
        "location": location,
        "candidate_data_sent": False,
        "nvidia_calls": 0,
        "limits": limits.model_dump(mode="json"),
        "deadline_seconds": 240,
        "retrieval": None,
        "failure": None,
    }
    started = time.monotonic()
    try:
        async with asyncio.timeout(240):
            result = await retrieve_combined_market(
                goal,
                primary if primary is not None else build_primary_market_client(settings),
                enrichment_client=(
                    support if support is not None else build_enrichment_market_client(settings)
                ),
                limits=limits,
                max_pages=2,
            )
        report["retrieval"] = result.model_dump(mode="json")
        report["body_summary"] = [
            {
                "title": item.posting.original_title,
                "employer": item.posting.employer,
                "location": item.posting.location,
                "characters": len(item.primary_content.markdown),
                "content_quality": item.content_quality.value,
                "selected_content_source": item.selected_content_source,
                "enrichment_status": item.enrichment_status.value,
                "enrichment_reason": item.enrichment_reason,
            }
            for item in result.posting_evidence
        ]
    except (MarketIntelligenceError, TimeoutError) as error:
        report["failure"] = type(error).__name__
    report["elapsed_seconds"] = round(time.monotonic() - started, 2)
    secrets = tuple(
        value.get_secret_value()
        for name in type(settings).model_fields
        if isinstance(value := getattr(settings, name), SecretStr)
    )
    sanitizer = LocalModelInspector(secrets=secrets, max_events=1)
    sanitizer.record("retrieval_validation", **report)
    return sanitizer.events[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-live", action="store_true")
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--location", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.allow_live:
        parser.error("Explicit --allow-live is required for public provider requests.")
    if args.output.exists():
        parser.error("Choose a new output path; previous runs are preserved.")
    settings = Settings(_env_file=args.env_file)
    result = asyncio.run(run_retrieval(settings, role=args.role, location=args.location))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)
    summary = (result.get("retrieval") or {}).get("snapshot") or {}
    print(
        json.dumps(
            {
                "output": str(args.output),
                "failure": result["failure"],
                "elapsed_seconds": result["elapsed_seconds"],
                "validated_postings": summary.get("validated_posting_count"),
                "distinct_employers": summary.get("distinct_employer_count"),
                "nvidia_calls": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
