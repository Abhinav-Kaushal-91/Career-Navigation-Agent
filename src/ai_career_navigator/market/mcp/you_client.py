"""You.com MCP adapter using the official Streamable HTTP client."""

import json
import logging
import re
from contextlib import AsyncExitStack
from html.parser import HTMLParser
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
MAX_CONTENT_CHARACTERS = 40_000
MAX_HTML_CHARACTERS = 1_000_000
_PAGE_FIELDS = ("markdown", "content", "text", "html")
_CONTENT_FORMATS = ("markdown", "html", "metadata")


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


class _PageHTML(HTMLParser):
    """Read text and JSON-LD only; never execute scripts or follow page links."""

    _hidden = {"head", "script", "style", "noscript", "nav", "footer", "header", "template"}
    _blocks = {"p", "li", "div", "section", "article", "br", "h1", "h2", "h3", "h4"}

    def __init__(self, raw: str):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.json_ld: list[Any] = []
        self._hidden_depth = 0
        self._json_parts: list[str] | None = None
        self.clipped = len(raw) > MAX_HTML_CHARACTERS
        self.feed(raw[:MAX_HTML_CHARACTERS])
        self.close()

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            content_type = (dict(attrs).get("type") or "").split(";", 1)[0].strip().casefold()
            if content_type == "application/ld+json":
                self._json_parts = []
        if tag in self._hidden:
            self._hidden_depth += 1
        if tag in self._blocks and not self._hidden_depth:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag == "script" and self._json_parts is not None:
            try:
                self.json_ld.append(json.loads("".join(self._json_parts)))
            except (json.JSONDecodeError, RecursionError):
                pass
            self._json_parts = None
        if tag in self._hidden:
            self._hidden_depth = max(0, self._hidden_depth - 1)
        if tag in self._blocks and not self._hidden_depth:
            self.parts.append("\n")

    def handle_data(self, data):
        if self._json_parts is not None:
            self._json_parts.append(data)
        elif not self._hidden_depth:
            self.parts.append(data)

    @property
    def text(self) -> str:
        return "\n".join(
            cleaned
            for line in "".join(self.parts).splitlines()
            if (cleaned := " ".join(line.split()))
        )


def _content_pages(payload: Any) -> list[dict[str, Any]]:
    """Only traverse response envelopes, not arbitrary nested metadata mappings."""
    pending = [(payload, 0)]
    pages = []
    visited = 0
    while pending:
        value, depth = pending.pop()
        visited += 1
        if depth > 8 or visited > 256:
            raise MarketContentError("You.com content response exceeded structural limits")
        if isinstance(value, list):
            pending.extend((item, depth + 1) for item in value)
        elif isinstance(value, dict):
            if any(
                key in value and isinstance(value[key], (str, type(None))) for key in _PAGE_FIELDS
            ):
                pages.append(value)
            else:
                for key in (
                    "pages", "contents", "results", "data", "response", "content", "output"
                ):
                    if key in value and isinstance(value[key], (dict, list)):
                        pending.append((value[key], depth + 1))
    return pages


def _page_url_key(value: Any) -> tuple | None:
    if not isinstance(value, str) or not value.strip() or len(value) > 2048:
        return None
    try:
        parts = urlsplit(value)
    except ValueError:
        return None
    if parts.scheme not in {"https", "http"} or not parts.netloc:
        return None
    # Do not strip query parameters that may identify different vacancies.
    return parts.scheme.casefold(), parts.netloc.casefold(), parts.path.rstrip("/"), parts.query


def _select_content_page(payload: Any, requested_url: str) -> dict[str, Any]:
    pages = _content_pages(payload)
    requested = _page_url_key(requested_url)
    matching = [page for page in pages if requested and _page_url_key(page.get("url")) == requested]
    candidates = matching or pages
    if len(candidates) != 1:
        raise MarketContentError("You.com content response did not identify one requested page")
    page = candidates[0]
    if page.get("url") is not None and _page_url_key(page["url"]) is None:
        raise MarketContentError("You.com content response contained an invalid returned URL")
    # A single returned redirect remains visible in page.url; service identity
    # validation, not this adapter, decides whether it is the same vacancy.
    return page


def _structured_jobs(values: list[Any]) -> list[dict[str, Any]]:
    pending = [(value, 0) for value in values]
    records = []
    fingerprints = set()
    visited = 0
    while pending:
        value, depth = pending.pop()
        visited += 1
        if depth > 24 or visited > 2048:
            raise MarketContentError("You.com structured metadata exceeded structural limits")
        if isinstance(value, list):
            pending.extend((item, depth + 1) for item in value)
        elif isinstance(value, dict):
            types = value.get("@type", [])
            types = [types] if isinstance(types, str) else types
            if isinstance(types, list) and any(
                item
                in {"JobPosting", "https://schema.org/JobPosting", "http://schema.org/JobPosting"}
                for item in types
                if isinstance(item, str)
            ):
                fingerprint = json.dumps(value, sort_keys=True, ensure_ascii=False)
                if fingerprint not in fingerprints:
                    records.append(value)
                    fingerprints.add(fingerprint)
            for key, child in value.items():
                if key in {"json_ld", "jsonld", "json-ld", "structured_data"} and isinstance(
                    child, str
                ):
                    if len(child) <= MAX_HTML_CHARACTERS:
                        try:
                            child = json.loads(child)
                        except (json.JSONDecodeError, RecursionError):
                            continue
                if isinstance(child, (dict, list)):
                    pending.append((child, depth + 1))
    return records


def _plain_content(value: str) -> tuple[str, bool]:
    if re.search(r"</?(?:p|li|div|section|article|script|html|body|br|h[1-6])\b", value, re.I):
        parsed = _PageHTML(value)
        return parsed.text, parsed.clipped
    return value, False


def _metadata_text(value: Any) -> str | None:
    text = _optional_text(value)
    if text is not None and len(text) > 2048:
        raise MarketContentError("You.com posting metadata exceeded text limits")
    return text


def _structured_location(raw: Any) -> str | None:
    places = raw if isinstance(raw, list) else [raw]
    if len(places) > 32:
        raise MarketContentError("You.com posting metadata exceeded location limits")
    locations = []
    for place in places:
        if not isinstance(place, dict):
            continue
        address = place.get("address", {})
        if isinstance(address, str):
            location = _metadata_text(address)
        elif isinstance(address, dict):
            parts = []
            for key in ("addressLocality", "addressRegion", "addressCountry"):
                value = address.get(key)
                if isinstance(value, dict):
                    value = value.get("name")
                if text := _metadata_text(value):
                    parts.append(text)
            location = ", ".join(parts)
        else:
            location = None
        if location and location not in locations:
            locations.append(location)
    return _metadata_text("; ".join(locations))


def normalize_you_content_payload(payload: Any, requested_url: str) -> MarketPageContent:
    item = _select_content_page(payload, requested_url)
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    html = item.get("html")
    parsed = _PageHTML(html) if isinstance(html, str) and html.strip() else None
    job_records = _structured_jobs([metadata, *(parsed.json_ld if parsed else [])])
    if len(job_records) > 1:
        raise MarketContentError("You.com page contains multiple distinct JobPosting records")
    job = job_records[0] if len(job_records) == 1 else {}
    organization = job.get("hiringOrganization", {})
    organization = organization if isinstance(organization, dict) else {}
    location = _structured_location(job.get("jobLocation", {}))
    identifier = job.get("identifier", {})
    identifier = identifier.get("value") if isinstance(identifier, dict) else identifier
    # Never join a site-wide page body to one isolated job's structured description.
    description = _optional_text(job.get("description"))
    clipped = bool(parsed and parsed.clipped)
    if description:
        content, description_clipped = _plain_content(description)
        clipped |= description_clipped
        for key, label in (
            ("responsibilities", "Responsibilities"),
            ("qualifications", "Qualifications"),
        ):
            section = _optional_text(job.get(key))
            if section:
                section, section_clipped = _plain_content(section)
                clipped |= section_clipped
                if section not in content:
                    content += f"\n{label}\n{section}"
    else:
        content = next(
            (
                value
                for key in ("markdown", "content", "text")
                if (value := _optional_text(item.get(key)))
            ),
            parsed.text if parsed else "",
        )
        content, text_clipped = _plain_content(content)
        clipped |= text_clipped
    clipped |= len(content) > MAX_CONTENT_CHARACTERS
    content = content[:MAX_CONTENT_CHARACTERS]
    if not content.strip():
        raise MarketContentError("You.com content response contained no usable page body")
    title = _metadata_text(job.get("title") or item.get("title") or metadata.get("title"))
    employer = _metadata_text(
        organization.get("name") or item.get("employer") or metadata.get("employer")
    )
    responsibilities_present = bool(
        _optional_text(job.get("responsibilities"))
        or re.search(r"\b(responsibilities|duties|what you.ll do)\b", content, re.I)
    )
    qualifications_present = bool(
        _optional_text(job.get("qualifications"))
        or re.search(r"\b(qualifications|requirements|what you.ll bring)\b", content, re.I)
    )
    complete = bool(
        description and title and employer and responsibilities_present and qualifications_present
    )
    canonical_url = _metadata_text(job.get("url") or item.get("canonical_job_url"))
    if canonical_url and _page_url_key(canonical_url) is None:
        raise MarketContentError("You.com structured posting contained an invalid canonical URL")
    return MarketPageContent(
        url=str(item.get("url") or requested_url),
        title=title,
        markdown=content,
        employer=employer,
        location=_metadata_text(location or item.get("location") or metadata.get("location")),
        work_mode=_metadata_text(item.get("work_mode") or metadata.get("work_mode")),
        employment_type=_metadata_text(
            job.get("employmentType")
            or item.get("employment_type")
            or metadata.get("employment_type")
        ),
        seniority=_metadata_text(item.get("seniority") or metadata.get("seniority")),
        posting_date=_metadata_text(
            job.get("datePosted") or item.get("posting_date") or metadata.get("posting_date")
        ),
        closing_date=_metadata_text(
            job.get("validThrough") or item.get("closing_date") or metadata.get("closing_date")
        ),
        active_status=_metadata_text(item.get("active_status") or metadata.get("active_status")),
        requisition_id=_metadata_text(
            identifier or item.get("requisition_id") or metadata.get("requisition_id")
        ),
        canonical_job_url=canonical_url,
        content_complete=False if clipped else True if complete else None,
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
        self._content_formats = list(_CONTENT_FORMATS)
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
            format_schema = properties.get("formats", {}).get("items", {})
            format_choices = format_schema.get("enum")
            self._content_formats = [
                value
                for value in _CONTENT_FORMATS
                if not isinstance(format_choices, list) or value in format_choices
            ]
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
        for value, supported_names in (
            (request.included_domains, ("include_domains", "included_domains")),
            (request.boosted_domains, ("boost_domains", "boosted_domains")),
        ):
            supported = next(
                (name for name in supported_names if name in self._search_properties), None
            )
            if value and supported:
                arguments[supported] = value
            elif value and supported_names[0] == "include_domains":
                domains = " OR ".join(f"site:{domain}" for domain in value)
                arguments["query"] += f" ({domains})"
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
            arguments["query"] += f" {exclusions}"
        payload = await self._call("you-search", arguments)
        return normalize_you_search_payload(payload)

    async def fetch_content(self, url: str) -> MarketPageContent:
        value: str | list[str] = url if self._content_argument == "url" else [url]
        arguments: dict[str, Any] = {self._content_argument: value}
        if self._content_supports_formats and self._content_formats:
            arguments["formats"] = self._content_formats
        payload = await self._call("you-contents", arguments)
        return normalize_you_content_payload(payload, url)
