"""You.com MCP adapter using the official Streamable HTTP client."""

import json
import logging
from contextlib import AsyncExitStack
from time import perf_counter
from types import TracebackType
from typing import Any, Self
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.types import CallToolResult, TextContent

from ai_career_navigator.config import Settings
from ai_career_navigator.market.errors import (
    MarketAuthenticationError,
    MarketConfigurationError,
    MarketContentError,
    MarketIntelligenceError,
    MarketRateLimitError,
    MarketTimeoutError,
    MarketToolError,
    MarketTransportError,
)
from ai_career_navigator.market.normalization import source_domain
from ai_career_navigator.market.schemas import (
    MarketPageContent,
    MarketSearchRequest,
    MarketSearchResult,
)

logger = logging.getLogger(__name__)
APPROVED_TOOLS = frozenset({"you-search", "you-contents"})


def _scoped_endpoint(endpoint: str) -> str:
    parts = urlsplit(endpoint)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["tools"] = "you-search,you-contents"
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))


def _payload(result: CallToolResult) -> Any:
    if result.is_error:
        raise MarketToolError("You.com MCP tool returned an error")
    if result.structured_content is not None:
        return result.structured_content
    text = "".join(block.text for block in result.content if isinstance(block, TextContent))
    if not text:
        raise MarketToolError("You.com MCP tool returned no usable content")
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise MarketToolError("You.com MCP tool returned malformed content") from error


def _walk_mappings(value: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        found.append(value)
        for child in value.values():
            found.extend(_walk_mappings(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_walk_mappings(child))
    return found


def normalize_you_search_payload(payload: Any) -> list[MarketSearchResult]:
    results: list[MarketSearchResult] = []
    seen: set[str] = set()
    for item in _walk_mappings(payload):
        url = item.get("url")
        title = item.get("title") or item.get("name")
        if not isinstance(url, str) or not isinstance(title, str) or url in seen:
            continue
        raw_snippets = item.get("snippets", item.get("snippet", item.get("description", [])))
        if isinstance(raw_snippets, str):
            snippets = [raw_snippets]
        elif isinstance(raw_snippets, list):
            snippets = [part for part in raw_snippets if isinstance(part, str)]
        else:
            snippets = []
        results.append(
            MarketSearchResult(
                title=title,
                url=url,
                snippets=snippets,
                source_domain=source_domain(url),
            )
        )
        seen.add(url)
    return results


def normalize_you_content_payload(payload: Any, requested_url: str) -> MarketPageContent:
    mappings = _walk_mappings(payload)
    item = next(
        (
            candidate
            for candidate in mappings
            if candidate.get("url") == requested_url
            and any(key in candidate for key in ("markdown", "content", "text", "html"))
        ),
        None,
    )
    if item is None:
        item = next(
            (
                candidate
                for candidate in mappings
                if any(key in candidate for key in ("markdown", "content", "text", "html"))
            ),
            None,
        )
    if item is None:
        raise MarketContentError("You.com MCP content response was malformed")
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    content = item.get("markdown", item.get("content", item.get("text", item.get("html", ""))))
    return MarketPageContent(
        url=str(item.get("url") or requested_url),
        title=_optional_text(item.get("title") or metadata.get("title")),
        markdown=content if isinstance(content, str) else "",
        employer=_optional_text(item.get("employer") or metadata.get("employer")),
        location=_optional_text(item.get("location") or metadata.get("location")),
        work_mode=_optional_text(item.get("work_mode") or metadata.get("work_mode")),
        employment_type=_optional_text(
            item.get("employment_type") or metadata.get("employment_type")
        ),
        seniority=_optional_text(item.get("seniority") or metadata.get("seniority")),
        posting_date=_optional_text(
            item.get("posting_date") or metadata.get("posting_date") or metadata.get("date")
        ),
        closing_date=_optional_text(item.get("closing_date") or metadata.get("closing_date")),
        active_status=_optional_text(item.get("active_status") or metadata.get("active_status")),
    )


def _optional_text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _safe_market_error(error: Exception) -> MarketIntelligenceError:
    message = str(error).casefold()
    status_code = getattr(getattr(error, "response", None), "status_code", None)
    if status_code in {401, 403} or "unauthorized" in message or "authentication" in message:
        return MarketAuthenticationError("You.com MCP authentication failed")
    if status_code == 429 or "rate limit" in message:
        return MarketRateLimitError("You.com MCP rate limit reached")
    if isinstance(error, (TimeoutError, httpx2.TimeoutException)) or "timeout" in message:
        return MarketTimeoutError("You.com MCP request timed out")
    return MarketTransportError("You.com MCP is temporarily unavailable")


class YouMcpMarketSearchClient:
    """Authenticated, allowlisted adapter; provider types never escape this class."""

    def __init__(self, *, endpoint: str, api_key: str, timeout_seconds: float) -> None:
        if not api_key.strip():
            raise MarketConfigurationError("YDC_API_KEY is required for market content retrieval")
        self._endpoint = _scoped_endpoint(endpoint)
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._stack: AsyncExitStack | None = None
        self._client: Client | None = None
        self._content_argument = "urls"
        self._content_supports_formats = True
        self._search_properties: set[str] = {"query"}

    def __repr__(self) -> str:
        return f"{type(self).__name__}(endpoint={self._endpoint!r}, api_key=<redacted>)"

    @classmethod
    def from_settings(cls, settings: Settings) -> "YouMcpMarketSearchClient":
        if settings.ydc_api_key is None:
            raise MarketConfigurationError("YDC_API_KEY is required for market content retrieval")
        return cls(
            endpoint=settings.you_mcp_url,
            api_key=settings.ydc_api_key.get_secret_value(),
            timeout_seconds=settings.market_timeout_seconds,
        )

    async def __aenter__(self) -> Self:
        stack = AsyncExitStack()
        try:
            http_client = await stack.enter_async_context(
                httpx2.AsyncClient(
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "X-Allowed-Tools": "you-search,you-contents",
                    },
                    timeout=self._timeout_seconds,
                    follow_redirects=True,
                )
            )
            transport = streamable_http_client(self._endpoint, http_client=http_client)
            client = await stack.enter_async_context(
                Client(transport, read_timeout_seconds=self._timeout_seconds)
            )
            listed = await client.list_tools()
            discovered = {tool.name for tool in listed.tools}
            if discovered != APPROVED_TOOLS:
                raise MarketConfigurationError("You.com MCP tool allowlist was not enforced")
            content_tool = next(tool for tool in listed.tools if tool.name == "you-contents")
            search_tool = next(tool for tool in listed.tools if tool.name == "you-search")
            self._search_properties = set(search_tool.input_schema.get("properties", {}))
            properties = content_tool.input_schema.get("properties", {})
            self._content_argument = (
                "url" if "url" in properties and "urls" not in properties else "urls"
            )
            self._content_supports_formats = "formats" in properties
        except MarketIntelligenceError:
            await stack.aclose()
            raise
        except Exception as error:
            await stack.aclose()
            raise _safe_market_error(error) from error
        self._stack = stack
        self._client = client
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._stack is not None:
            await self._stack.aclose()
        self._stack = None
        self._client = None

    async def _call(self, tool: str, arguments: dict[str, Any]) -> Any:
        if tool not in APPROVED_TOOLS:
            raise MarketConfigurationError("market adapter attempted an unapproved MCP tool")
        if self._client is None:
            raise MarketConfigurationError("market client must be used as an async context manager")
        started = perf_counter()
        try:
            result = await self._client.call_tool(
                tool,
                arguments,
                read_timeout_seconds=self._timeout_seconds,
            )
            return _payload(result)
        except MarketIntelligenceError as error:
            logger.warning("market_tool_failed tool=%s category=%s", tool, type(error).__name__)
            raise
        except Exception as error:
            wrapped = _safe_market_error(error)
            logger.warning("market_tool_failed tool=%s category=%s", tool, type(wrapped).__name__)
            raise wrapped from error
        finally:
            logger.info(
                "market_tool_completed tool=%s latency_ms=%d",
                tool,
                (perf_counter() - started) * 1000,
            )

    async def search(self, request: MarketSearchRequest) -> list[MarketSearchResult]:
        query = request.query
        arguments: dict[str, Any] = {"query": query}
        optional = {
            "count": request.count,
            "country": request.country,
            "language": request.language,
            "freshness": request.freshness.value,
        }
        for name, value in optional.items():
            if name in self._search_properties:
                arguments[name] = value
        exclusion_name = next(
            (
                name
                for name in ("exclude_domains", "excluded_domains")
                if name in self._search_properties
            ),
            None,
        )
        if request.excluded_domains and exclusion_name is not None:
            arguments[exclusion_name] = request.excluded_domains
        elif request.excluded_domains:
            exclusions = " ".join(f"-site:{domain}" for domain in request.excluded_domains)
            arguments["query"] = f"{query} {exclusions}"
        payload = await self._call("you-search", arguments)
        return normalize_you_search_payload(payload)

    async def fetch_content(self, url: str) -> MarketPageContent:
        value: str | list[str] = url if self._content_argument == "url" else [url]
        arguments: dict[str, Any] = {self._content_argument: value}
        if self._content_supports_formats:
            arguments["formats"] = ["markdown"]
        payload = await self._call("you-contents", arguments)
        return normalize_you_content_payload(payload, url)
