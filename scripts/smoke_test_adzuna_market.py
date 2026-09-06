"""Manual-only smoke test for the structured Adzuna market adapter."""

import argparse
import asyncio
from collections.abc import Sequence
from pathlib import Path

from ai_career_navigator.config import Settings
from ai_career_navigator.market import (
    StructuredJobSearchRequest,
    build_primary_market_client,
)


def _settings(path: Path) -> Settings:
    if not path.is_file():
        raise SystemExit(f"Environment file not found: {path}")
    settings = Settings(_env_file=path)
    if settings.adzuna_app_id is None or settings.adzuna_app_key is None:
        raise SystemExit(
            "ADZUNA_APP_ID and ADZUNA_APP_KEY are required; values will not be printed."
        )
    return settings


async def _run(settings: Settings, *, role: str, location: str) -> None:
    client = build_primary_market_client(settings)
    request = StructuredJobSearchRequest(
        title=role,
        location=location,
        page=1,
        results_per_page=10,
    )
    async with client:
        response = await client.search_page(request)
    print("provider=adzuna")
    print("connection=succeeded")
    print(f"query_role={role}")
    print(f"query_location={location}")
    print(f"normalized_result_count={len(response.results)}")
    print(f"provider_reported_count={response.total_available}")
    print(f"malformed_result_count={response.malformed_result_count}")
    for result in response.results[:3]:
        print(
            f"title={result.title[:120]!r} "
            f"company={(result.company or 'unknown')[:120]!r} "
            f"location={(result.location or 'unknown')[:120]!r}"
        )


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--role", default="AI Solutions Architect")
    parser.add_argument("--location", default="Canada")
    args = parser.parse_args(argv)
    asyncio.run(_run(_settings(args.env_file), role=args.role, location=args.location))


if __name__ == "__main__":
    main()
