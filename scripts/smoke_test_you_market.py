"""Explicit manual-only smoke test for the allowlisted You.com MCP adapter."""

import argparse
import asyncio
from collections.abc import Callable, Sequence
from pathlib import Path

from ai_career_navigator.config import Settings
from ai_career_navigator.market.mcp import YouMcpMarketSearchClient
from ai_career_navigator.market.schemas import (
    MarketSearchRequest,
    SearchFreshness,
    SearchPassType,
)

QUERY = '"AI Solutions Architect" jobs Toronto Canada'
SAFE_TOOLS = ("you-contents", "you-search")
ClientFactory = Callable[[Settings], YouMcpMarketSearchClient]


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env-file",
        type=Path,
        help="Local environment file read through Settings; secret values are never printed.",
    )
    parser.add_argument(
        "--fetch-first",
        action="store_true",
        help="Retrieve one result page and print metadata only.",
    )
    return parser.parse_args(argv)


def _load_settings(env_file: Path | None) -> Settings:
    if env_file is None:
        return Settings()
    if not env_file.is_file():
        raise SystemExit(f"Environment file not found: {env_file}")
    return Settings(_env_file=env_file)


async def run(
    *,
    settings: Settings,
    fetch_first: bool,
    client_factory: ClientFactory = YouMcpMarketSearchClient.from_settings,
) -> None:
    if settings.ydc_api_key is None or not settings.ydc_api_key.get_secret_value().strip():
        raise SystemExit("YDC_API_KEY is required. The key will not be printed.")

    client = client_factory(settings)
    async with client:
        print("mcp_connection=connected")
        tools = ",".join(SAFE_TOOLS)
        print(f"allowed_tools={tools}")
        print(f"discovered_tools={tools}")
        print(f"query={QUERY}")
        results = await client.search(
            MarketSearchRequest(
                query=QUERY,
                pass_type=SearchPassType.GENERAL_WEB,
                freshness=SearchFreshness.MONTH,
            )
        )
        print(f"search_result_count={len(results)}")
        for result in results[:3]:
            print(f"title={result.title[:120]!r} domain={result.source_domain or 'unknown'}")
        if fetch_first and results:
            content = await client.fetch_content(results[0].url)
            title = content.title[:120] if content.title else "unknown"
            print(
                "first_content_retrieval=succeeded "
                f"domain={results[0].source_domain or 'unknown'} "
                f"title={title!r} "
                f"content_characters={len(content.markdown)}"
            )
        elif fetch_first:
            print("first_content_retrieval=skipped_no_results")
        else:
            print("first_content_retrieval=not_requested")


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    settings = _load_settings(args.env_file)
    asyncio.run(run(settings=settings, fetch_first=args.fetch_first))


if __name__ == "__main__":
    main()
