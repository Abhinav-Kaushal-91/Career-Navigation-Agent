"""JSearch via RapidAPI. Credentials never enter normalized evidence or request URLs."""

import asyncio
import logging
import re
from datetime import datetime
from time import monotonic

import httpx

from ai_career_navigator.market.errors import (
    MarketAuthenticationError,
    MarketConfigurationError,
    MarketContentError,
    MarketRateLimitError,
    MarketTimeoutError,
    MarketTransportError,
)
from ai_career_navigator.market.normalization import canonicalize_url
from ai_career_navigator.market.schemas import (
    MarketSourceProvider,
    StructuredJobResult,
    StructuredJobSearchPage,
)

HOST = "jsearch.p.rapidapi.com"
logger = logging.getLogger(__name__)


def text(value):
    return value.strip() if isinstance(value, str) and value.strip() else None


def parsed_date(value):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date() if value else None
    except (AttributeError, TypeError, ValueError):
        return None


def description_incomplete(description):
    # Request details for missing/visibly truncated descriptions, not a length cutoff.
    return not description.strip() or bool(
        re.search(r"(?:\.\.\.|…|\bread more|\bshow more)\s*$", description, re.I)
    )


def posting_description(raw):
    """Only job-content fields may become analysis text; never salary/benefit metadata."""
    description = text(raw.get("job_description"))
    if description:
        return description, "SEARCH_DESCRIPTION"
    highlights = raw.get("job_highlights")
    sections = []
    if isinstance(highlights, dict):
        for name in ("Responsibilities", "Qualifications"):
            values = highlights.get(name)
            if isinstance(values, list):
                lines = [text(value) for value in values if text(value)]
                if lines:
                    sections.append(name + "\n" + "\n".join(lines))
    return "\n\n".join(sections), "SEARCH_HIGHLIGHTS" if sections else "MISSING"


def application_url(raw):
    """Application options are alternatives for one job, not additional vacancies."""
    options = raw.get("apply_options")
    candidates = [raw.get("job_apply_link")]
    if isinstance(options, list):
        candidates.extend(o.get("apply_link") for o in options if isinstance(o, dict))
    for candidate in candidates:
        if isinstance(candidate, str) and canonicalize_url(candidate):
            return candidate.strip()
    return None


def normalize_jsearch_payload(payload):
    if not isinstance(payload, dict) or payload.get("status") != "OK":
        raise MarketContentError("JSearch did not return a successful response")
    data = payload.get("data")
    has_more = isinstance(data, dict) and bool(text(data.get("cursor")))
    # v1/details return a list; Search V2 wraps jobs and cursor in data.
    if isinstance(data, dict):
        data = data.get("jobs")
    if not isinstance(data, list):
        raise MarketContentError("JSearch returned malformed job data")
    results, malformed, issues = [], 0, []
    for index, raw in enumerate(data[:50]):
        if not isinstance(raw, dict):
            malformed += 1
            issues.append(f"Result {index + 1}: expected a job object")
            continue
        try:
            description, origin = posting_description(raw)
            country = text(raw.get("job_country"))
            country = {"ca": "Canada", "us": "United States"}.get((country or "").lower(), country)
            location = ", ".join(
                filter(
                    None,
                    [
                        text(raw.get("job_city")),
                        text(raw.get("job_state")),
                        country,
                    ],
                )
            )
            # If structured locality fields are absent, retain the supplied display location
            # instead of allowing the country alone to mask a more precise location.
            if not text(raw.get("job_city")) and not text(raw.get("job_state")):
                location = text(raw.get("job_location")) or location
            url = application_url(raw)
            if not url or not text(raw.get("job_id")) or not text(raw.get("job_title")):
                raise ValueError("Missing posting identity, title or valid application URL")
            results.append(
                StructuredJobResult(
                    provider=MarketSourceProvider.JSEARCH,
                    provider_job_id=text(raw.get("job_id")),
                    title=text(raw.get("job_title")),
                    url=url,
                    description=description,
                    # The provider supplies description text, not independent completeness proof.
                    content_complete=False
                    if origin != "SEARCH_DESCRIPTION" or description_incomplete(description)
                    else None,
                    company=text(raw.get("employer_name")),
                    location=location,
                    created=parsed_date(raw.get("job_posted_at_datetime_utc")),
                    closing_date=parsed_date(raw.get("job_offer_expiration_datetime_utc")),
                    contract_type=text(raw.get("job_employment_type")),
                    active_status="PROVIDER_OBSERVED",
                    provider_stable_id=text(raw.get("job_uid")),
                    publisher=text(raw.get("job_publisher")),
                    reported_location=text(raw.get("job_location")),
                    is_remote=raw.get("job_is_remote")
                    if isinstance(raw.get("job_is_remote"), bool)
                    else None,
                    application_is_direct=raw.get("job_apply_is_direct")
                    if isinstance(raw.get("job_apply_is_direct"), bool)
                    else None,
                    description_origin=origin,
                )
            )
        except (TypeError, ValueError):
            malformed += 1
            issues.append(
                f"Result {index + 1}: missing or invalid posting identity/title/application URL"
            )
    return StructuredJobSearchPage(
        provider=MarketSourceProvider.JSEARCH,
        page=1,
        results=results,
        malformed_result_count=malformed,
        input_result_count=len(data),
        deferred_result_count=max(0, len(data) - 50),
        continuation_available=has_more,
        response_request_id=text(payload.get("request_id")),
        normalization_issues=issues,
    )


class JSearchMarketClient:
    provider = MarketSourceProvider.JSEARCH

    def __init__(
        self,
        *,
        api_key,
        timeout=30,
        search_timeout=90,
        search_path="/search-v2",
        country="ca",
        max_details=5,
        transport=None,
    ):
        if not api_key or not api_key.strip():
            raise MarketConfigurationError("Add RAPIDAPI_KEY to .env and subscribe to JSearch.")
        if search_path not in {"/search", "/search-v2"}:
            raise MarketConfigurationError("Unsupported JSearch search endpoint")
        self._key, self._timeout, self._transport = api_key, timeout, transport
        self._search_timeout = search_timeout
        self.search_path, self.country, self.max_details = search_path, country, max_details
        self._client = None

    def __repr__(self):
        return "JSearchMarketClient(api_key=<redacted>)"

    @classmethod
    def from_settings(cls, settings):
        return cls(
            api_key=settings.rapidapi_key.get_secret_value() if settings.rapidapi_key else None,
            timeout=settings.market_timeout_seconds,
            search_timeout=settings.jsearch_search_timeout_seconds,
            search_path=settings.jsearch_search_path,
            country=settings.jsearch_country,
            max_details=settings.jsearch_max_details,
        )

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            base_url=f"https://{HOST}",
            timeout=self._timeout,
            transport=self._transport,
            follow_redirects=False,
            headers={
                "X-RapidAPI-Key": self._key,
                "X-RapidAPI-Host": HOST,
                "Accept": "application/json",
            },
        )
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()
        self._client = None

    async def _get(self, path, params, *, read_timeout=None):
        if not self._client:
            raise MarketConfigurationError("Use JSearch within its async context")
        read_budget = self._timeout if read_timeout is None else read_timeout
        request_timeout = httpx.Timeout(
            read_budget,
            connect=min(10, read_budget),
            write=min(10, read_budget),
            pool=min(10, read_budget),
        )
        started = monotonic()
        try:
            # One request only. Bound total time too, in case a server trickles bytes.
            async with asyncio.timeout(read_budget + 10):
                response = await self._client.get(path, params=params, timeout=request_timeout)
            if response.status_code in {401, 403}:
                raise MarketAuthenticationError("Check RAPIDAPI_KEY and your JSearch subscription.")
            if response.status_code == 429:
                raise MarketRateLimitError(
                    "JSearch quota or rate limit reached; no automatic retry."
                )
            response.raise_for_status()
            return normalize_jsearch_payload(response.json())
        except (httpx.TimeoutException, TimeoutError) as error:
            logger.warning(
                "jsearch_request_timeout endpoint=%s phase=%s "
                "read_budget_seconds=%s elapsed_seconds=%.2f",
                path,
                type(error).__name__,
                read_budget,
                monotonic() - started,
            )
            raise MarketTimeoutError("JSearch request timed out") from None
        except httpx.HTTPError:
            raise MarketTransportError(
                "JSearch request failed; check endpoint and service status"
            ) from None
        except ValueError:
            raise MarketContentError("JSearch returned invalid JSON") from None

    async def search_page(self, request):
        params = {
            "query": f"{request.title} in {request.location.lower()}",
            # Match the Canadian playground request verified by the user and live probe.
            # Keep internal country codes unchanged, including for Job Details.
            "country": "canada" if request.country == "ca" else request.country,
            "language": "en",
            "date_posted": "all",
            "num_pages": 1,
        }
        if self.search_path == "/search":
            params.update(page=1, num_pages=1)
        return await self._get(self.search_path, params, read_timeout=self._search_timeout)

    async def job_details(self, job_id, *, country):
        page = await self._get(
            "/job-details",
            {
                "job_id": job_id,
                "country": country,
                "language": "en",
            },
        )
        return next((item for item in page.results if item.provider_job_id == job_id), None)
