import asyncio

import httpx
import pytest

from ai_career_navigator.config import Settings
from ai_career_navigator.market import (
    AdzunaMarketSearchClient,
    MarketAuthenticationError,
    MarketConfigurationError,
    MarketContentError,
    StructuredJobSearchRequest,
    normalize_adzuna_payload,
)


def payload() -> dict[str, object]:
    return {
        "count": 1,
        "results": [
            {
                "id": "adz-1",
                "title": "AI Solutions Architect",
                "description": "Build production AI systems.",
                "redirect_url": "https://example.ca/jobs/adz-1",
                "created": "2026-09-01T12:30:00Z",
                "company": {"display_name": "Example Corp"},
                "location": {"display_name": "Toronto, Ontario"},
                "category": {"label": "IT Jobs"},
                "contract_type": "permanent",
                "salary_min": 120000,
            }
        ],
    }


def test_normalizes_structured_adzuna_result() -> None:
    page = normalize_adzuna_payload(payload(), page=1)
    assert page.total_available == 1
    assert page.results[0].provider_job_id == "adz-1"
    assert page.results[0].company == "Example Corp"
    assert page.results[0].created.isoformat() == "2026-09-01"


def test_malformed_records_are_rejected_and_counted() -> None:
    raw = payload()
    raw["results"] = [*raw["results"], {"title": "Missing ID and URL"}]  # type: ignore[index]
    page = normalize_adzuna_payload(raw, page=1)
    assert len(page.results) == 1
    assert page.malformed_result_count == 1


def test_request_is_bounded_and_credentials_do_not_escape() -> None:
    secret_id = "private-id"
    secret_key = "private-key"

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/jobs/ca/search/2")
        assert request.url.params["results_per_page"] == "12"
        assert request.url.params["what"] == "AI Solutions Architect"
        assert request.url.params["where"] == "Canada"
        return httpx.Response(200, json=payload())

    client = AdzunaMarketSearchClient(
        app_id=secret_id,
        app_key=secret_key,
        base_url="https://api.adzuna.com/v1/api",
        timeout_seconds=2,
        transport=httpx.MockTransport(handler),
    )

    async def run() -> None:
        async with client:
            result = await client.search_page(
                StructuredJobSearchRequest(
                    title="AI Solutions Architect", location="Canada", page=2
                )
            )
        assert len(result.results) == 1

    asyncio.run(run())
    assert secret_id not in repr(client)
    assert secret_key not in repr(client)


def test_authentication_failure_maps_to_market_error() -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(401, json={}))
    client = AdzunaMarketSearchClient(
        app_id="id",
        app_key="key",
        base_url="https://api.adzuna.com/v1/api",
        timeout_seconds=2,
        transport=transport,
    )

    async def run() -> None:
        async with client:
            with pytest.raises(MarketAuthenticationError, match="authentication failed"):
                await client.search_page(
                    StructuredJobSearchRequest(title="AI Architect", location="Canada")
                )

    asyncio.run(run())


def test_malformed_json_maps_to_content_error() -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, content=b"not-json"))
    client = AdzunaMarketSearchClient(
        app_id="id",
        app_key="key",
        base_url="https://api.adzuna.com/v1/api",
        timeout_seconds=2,
        transport=transport,
    )

    async def run() -> None:
        async with client:
            with pytest.raises(MarketContentError, match="malformed JSON"):
                await client.search_page(
                    StructuredJobSearchRequest(title="AI Architect", location="Canada")
                )

    asyncio.run(run())


def test_settings_require_both_credentials() -> None:
    with pytest.raises(MarketConfigurationError, match="ADZUNA_APP_ID"):
        AdzunaMarketSearchClient.from_settings(Settings(_env_file=None))
