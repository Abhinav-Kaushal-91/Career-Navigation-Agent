"""One public URL content-contract diagnostic; print structure, never page bodies or keys."""

import argparse
import asyncio
import json
from pathlib import Path

from pydantic import SecretStr

from ai_career_navigator.config import Settings
from ai_career_navigator.market.errors import MarketContentError
from ai_career_navigator.market.mcp import you_client
from ai_career_navigator.models.inspection import LocalModelInspector


def shape(value, depth=0):
    if depth > 6:
        return type(value).__name__
    if isinstance(value, dict):
        return {key: shape(item, depth + 1) for key, item in list(value.items())[:20]}
    if isinstance(value, list):
        return {
            "type": "list",
            "length": len(value),
            "items": [shape(item, depth + 1) for item in value[:2]],
        }
    return {"type": type(value).__name__, "length": len(value) if isinstance(value, str) else None}


async def run(settings, url):
    normalize = you_client.normalize_you_content_payload
    sanitizer = LocalModelInspector(
        secrets=tuple(
            value.get_secret_value()
            for name in type(settings).model_fields
            if isinstance(value := getattr(settings, name), SecretStr)
        ),
        max_events=1,
    )

    def inspected(payload, requested_url):
        sanitizer.record("content_contract", response_shape=shape(payload))
        print(json.dumps(sanitizer.events[0]), flush=True)
        try:
            return normalize(payload, requested_url)
        except MarketContentError as error:
            # These messages are fixed literals in our content normalizer, never provider errors.
            print(json.dumps({"normalization_error": str(error)}), flush=True)
            raise

    you_client.normalize_you_content_payload = inspected
    try:
        async with you_client.YouMcpMarketSearchClient.from_settings(settings) as client:
            page = await client.fetch_content(url)
            print(json.dumps({"characters": len(page.markdown), "complete": page.content_complete}))
    except MarketContentError:
        pass
    finally:
        you_client.normalize_you_content_payload = normalize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-live", action="store_true")
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--url", required=True)
    args = parser.parse_args()
    if not args.allow_live:
        parser.error("--allow-live is required")
    asyncio.run(run(Settings(_env_file=args.env_file), args.url))


if __name__ == "__main__":
    main()
