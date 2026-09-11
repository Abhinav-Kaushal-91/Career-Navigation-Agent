"""Bounded live probes; no session changes, credentials or reasoning logs.

Default: You.com handshake and one tiny structured model call.
--search: additionally one two-result search per market provider.
--demo: replace the tiny model call with one synthetic demo strength review.
Live calls may consume provider credits. No inferred strengths are approved.
"""

import argparse
import asyncio

from pydantic import BaseModel

from ai_career_navigator.market.adzuna_client import AdzunaMarketSearchClient
from ai_career_navigator.market.mcp.you_client import YouMcpMarketSearchClient
from ai_career_navigator.market.schemas import (
    MarketSearchRequest,
    SearchFreshness,
    SearchPassType,
    StructuredJobSearchRequest,
)
from ai_career_navigator.models import ModelGateway, ModelRole
from ai_career_navigator.profile.inference import infer_capabilities
from ai_career_navigator.profile.service import build_candidate_profile
from ai_career_navigator.ui.demo_data import sample_profile_draft
from ai_career_navigator.ui.live_workflow import load_live_settings


def error_types(error):
    names = [type(error).__name__]
    for child in getattr(error, "exceptions", ()):
        names.extend(error_types(child))
    if error.__cause__ is not None:
        names.extend(error_types(error.__cause__))
    return names


async def market(settings, search, full_page=False):
    try:
        async with YouMcpMarketSearchClient.from_settings(settings) as client:
            print("You.com handshake OK", flush=True)
            if search:
                results = await client.search(
                    MarketSearchRequest(
                        query='"Senior Java Developer" Toronto jobs',
                        pass_type=SearchPassType.DIRECT_SOURCE,
                        freshness=SearchFreshness.MONTH,
                        count=2,
                        full_page=full_page,
                    )
                )
                print("You.com search returned:", len(results), flush=True)
                if full_page and results:
                    page = await client.fetch_content(results[0].url)
                    print("You.com first page words:", len(page.markdown.split()), flush=True)
    except Exception as error:
        print("You.com exception types:", error_types(error), flush=True)
    if search:
        try:
            async with AdzunaMarketSearchClient.from_settings(settings) as client:
                page = await client.search_page(
                    StructuredJobSearchRequest(
                        title="Senior Java Developer",
                        location="Toronto",
                        results_per_page=2,
                    )
                )
                print("Adzuna search returned:", len(page.results), flush=True)
        except Exception as error:
            print("Adzuna exception types:", error_types(error), flush=True)


class ConnectionCheck(BaseModel):
    ok: bool


def model(settings, demo):
    gateway = ModelGateway.from_settings(settings)
    if demo:
        profile = build_candidate_profile(sample_profile_draft(), approved=True)
        print(
            "Synthetic demo review started; evidence items:",
            len(profile.evidence_items),
            flush=True,
        )
        outcome = infer_capabilities(profile, gateway)
        print("Demo review:", outcome.status.value, "error:", outcome.error_category, flush=True)
        print("Pending strengths:", len(outcome.inferred_evidence), flush=True)
        for item in outcome.inferred_evidence:
            print("Suggested:", item.capability, flush=True)
        return
    try:
        response = gateway.generate_structured(
            role=ModelRole.EXTRACTION,
            output_schema=ConnectionCheck,
            system_prompt="Return JSON with ok true.",
            user_prompt="Connection check only.",
        )
        print("Production gateway OK; finish:", response.finish_reason, flush=True)
    except Exception as error:
        print("Gateway exception types:", error_types(error), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--search", action="store_true")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--full-page", action="store_true")
    parser.add_argument("--market-only", action="store_true")
    args = parser.parse_args()
    settings = load_live_settings().model_copy(
        update={"model_timeout_seconds": 180, "max_retries": 0}
    )
    print("Configured:", settings.llm_provider, settings.extraction_model, flush=True)
    asyncio.run(market(settings, args.search or args.full_page, args.full_page))
    if not args.market_only:
        model(settings, args.demo)
