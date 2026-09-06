import asyncio

from ai_career_navigator.market.mcp.you_client import (
    YouMcpMarketSearchClient,
    _scoped_endpoint,
    normalize_you_content_payload,
    normalize_you_search_payload,
)
from ai_career_navigator.market.schemas import (
    MarketSearchRequest,
    SearchFreshness,
    SearchPassType,
)


def test_search_forwards_supported_discovery_controls(monkeypatch) -> None:
    client = YouMcpMarketSearchClient(
        endpoint="https://api.you.com/mcp",
        api_key="not-printed",
        timeout_seconds=30,
    )
    client._search_properties = {  # noqa: SLF001
        "query",
        "count",
        "country",
        "language",
        "freshness",
        "exclude_domains",
    }
    observed: dict[str, object] = {}

    async def fake_call(tool: str, arguments: dict[str, object]) -> dict[str, object]:
        observed["tool"] = tool
        observed["arguments"] = arguments
        return {"results": {"web": []}}

    monkeypatch.setattr(client, "_call", fake_call)
    request = MarketSearchRequest(
        query='"AI Solutions Architect" Toronto Canada careers',
        pass_type=SearchPassType.DIRECT_SOURCE,
        freshness=SearchFreshness.MONTH,
        count=12,
        excluded_domains=["indeed.com"],
    )

    asyncio.run(client.search(request))

    assert observed == {
        "tool": "you-search",
        "arguments": {
            "query": request.query,
            "count": 12,
            "country": "CA",
            "language": "EN",
            "freshness": "month",
            "exclude_domains": ["indeed.com"],
        },
    }


def test_endpoint_is_restricted_to_approved_tools() -> None:
    endpoint = _scoped_endpoint("https://api.you.com/mcp?profile=paid")

    assert "profile=paid" in endpoint
    assert "tools=you-search%2Cyou-contents" in endpoint


def test_search_payload_is_normalized_without_provider_objects() -> None:
    results = normalize_you_search_payload(
        {
            "results": {
                "web": [
                    {
                        "title": "AI Solutions Architect",
                        "url": "https://example.com/jobs/1",
                        "snippets": ["Apply now"],
                    }
                ]
            }
        }
    )

    assert results[0].title == "AI Solutions Architect"
    assert results[0].source_domain == "example.com"


def test_content_payload_normalizes_metadata_conservatively() -> None:
    content = normalize_you_content_payload(
        {
            "contents": [
                {
                    "url": "https://example.com/jobs/1",
                    "markdown": "Responsibilities and qualifications",
                    "metadata": {"title": "AI Architect", "employer": "Example"},
                }
            ]
        },
        "https://example.com/jobs/1",
    )

    assert content.title == "AI Architect"
    assert content.employer == "Example"
    assert "Responsibilities" in content.markdown


def test_adapter_representation_redacts_api_key() -> None:
    secret = "do-not-print-this"
    client = YouMcpMarketSearchClient(
        endpoint="https://api.you.com/mcp",
        api_key=secret,
        timeout_seconds=30,
    )

    assert secret not in repr(client)
    assert "<redacted>" in repr(client)
