"""One explicitly requested JSearch search; no LLM calls or description-detail fan-out."""

import argparse
import asyncio

from ai_career_navigator.market.errors import MarketIntelligenceError
from ai_career_navigator.market.jsearch_client import JSearchMarketClient
from ai_career_navigator.market.schemas import StructuredJobSearchRequest
from ai_career_navigator.ui.live_workflow import load_live_settings


async def run(role, location):
    settings = load_live_settings()
    try:
        async with JSearchMarketClient.from_settings(settings) as client:
            result = await client.search_page(
                StructuredJobSearchRequest(
                    title=role,
                    location=location,
                    country=client.country,
                )
            )
        print(
            f"JSearch: {len(result.results)} jobs; {result.malformed_result_count} invalid records"
        )
        for item in result.results:
            print(
                f"{item.title} | {item.company} | {item.location} | "
                f"{len(item.description.split())} description words"
            )
    except MarketIntelligenceError as error:
        print(f"{type(error).__name__}: {error}")
        return 1
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", default="Senior Java Developer")
    parser.add_argument("--location", default="Toronto, Canada")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.role, args.location)))
