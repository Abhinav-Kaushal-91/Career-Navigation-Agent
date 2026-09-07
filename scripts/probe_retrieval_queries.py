"""Three explicit public-role query probes and at most three content fetches; no LLM."""

import argparse
import asyncio
import json
from pathlib import Path

from pydantic import SecretStr

from ai_career_navigator.config import Settings
from ai_career_navigator.market.errors import MarketIntelligenceError
from ai_career_navigator.market.mcp.you_client import YouMcpMarketSearchClient
from ai_career_navigator.market.schemas import MarketSearchRequest, SearchFreshness, SearchPassType
from ai_career_navigator.market.source_registry import (
    AGGREGATOR_SEARCH_DOMAINS,
    ATS_JOB_SEARCH_DOMAINS,
)
from ai_career_navigator.models.inspection import LocalModelInspector


async def run(settings):
    queries = [
        ('"Senior Java Developer" "Toronto" Canada', sorted(ATS_JOB_SEARCH_DOMAINS)),
        ('"Senior Java Developer" "Toronto" careers', []),
        ('"Senior Java Developer" "Targeted Talent" "Toronto"', []),
    ]
    records = []
    async with asyncio.timeout(180):
        async with YouMcpMarketSearchClient.from_settings(settings) as client:
            for query, domains in queries:
                request = MarketSearchRequest(
                    query=query,
                    pass_type=SearchPassType.GENERAL_WEB,
                    freshness=SearchFreshness.YEAR,
                    included_domains=domains,
                    excluded_domains=[] if domains else sorted(AGGREGATOR_SEARCH_DOMAINS),
                )
                try:
                    results = await client.search(request)
                    records.append(
                        {
                            "query": query,
                            "request": request.model_dump(mode="json"),
                            "results": [item.model_dump(mode="json") for item in results[:12]],
                        }
                    )
                except MarketIntelligenceError as error:
                    records.append({"query": query, "failure": type(error).__name__})
            urls = list(
                dict.fromkeys(
                    item["url"]
                    for record in records
                    for item in record.get("results", [])
                    if "toronto" in (item["title"] + " ".join(item["snippets"])).casefold()
                )
            )[:3]
            pages = []
            for url in urls:
                try:
                    page = await client.fetch_content(url)
                    pages.append(page.model_dump(mode="json"))
                except MarketIntelligenceError as error:
                    pages.append({"url": url, "failure": type(error).__name__})
    sanitizer = LocalModelInspector(
        secrets=tuple(
            value.get_secret_value()
            for name in type(settings).model_fields
            if isinstance(value := getattr(settings, name), SecretStr)
        ),
        max_events=1,
    )
    sanitizer.record("PUBLIC_QUERY_EXPERIMENT", queries=records, pages=pages, nvidia_calls=0)
    return sanitizer.events[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-live", action="store_true")
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.allow_live or args.output.exists():
        parser.error("--allow-live and a new output file are required")
    settings = Settings(_env_file=args.env_file).model_copy(update={"market_timeout_seconds": 25})
    result = asyncio.run(run(settings))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "searches": len(result["queries"]),
                "fetches": len(result["pages"]),
                "nvidia_calls": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
