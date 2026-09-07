"""Adzuna structured job-search adapter."""

from datetime import date, datetime
from types import TracebackType
from typing import Any, Self

import httpx

from ai_career_navigator.config import Settings
from ai_career_navigator.market.errors import (
    MarketAuthenticationError,
    MarketConfigurationError,
    MarketContentError,
    MarketRateLimitError,
    MarketTimeoutError,
    MarketTransportError,
)
from ai_career_navigator.market.schemas import (
    MarketSourceProvider,
    StructuredJobResult,
    StructuredJobSearchPage,
    StructuredJobSearchRequest,
)


def _text(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _nested_text(value: object, key: str) -> str | None:
    return _text(value.get(key)) if isinstance(value, dict) else None


def _date(value: object) -> date | None:
    text = _text(value)
    if text is None:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def normalize_adzuna_payload(payload: object, *, page: int) -> StructuredJobSearchPage:
    """Reject malformed records while retaining a count for evidence quality."""

    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        raise MarketContentError("Adzuna returned a malformed search response")
    normalized: list[StructuredJobResult] = []
    malformed = 0
    for raw in payload["results"]:
        if not isinstance(raw, dict):
            malformed += 1
            continue
        provider_id = _text(raw.get("id"))
        title = _text(raw.get("title"))
        url = _text(raw.get("redirect_url"))
        if not provider_id or not title or not url:
            malformed += 1
            continue
        try:
            normalized.append(
                StructuredJobResult(
                    provider=MarketSourceProvider.ADZUNA,
                    provider_job_id=provider_id,
                    title=title,
                    url=url,
                    description=_text(raw.get("description")) or "",
                    # Adzuna's search contract supplies a snippet, not a full description.
                    content_complete=False,
                    company=_nested_text(raw.get("company"), "display_name"),
                    location=_nested_text(raw.get("location"), "display_name"),
                    created=_date(raw.get("created")),
                    category=_nested_text(raw.get("category"), "label"),
                    contract_type=_text(raw.get("contract_type")),
                    salary_min=raw.get("salary_min"),
                    salary_max=raw.get("salary_max"),
                )
            )
        except (TypeError, ValueError):
            malformed += 1
    count = payload.get("count")
    total = count if isinstance(count, int) and count >= 0 else None
    return StructuredJobSearchPage(
        provider=MarketSourceProvider.ADZUNA,
        page=page,
        total_available=total,
        results=normalized,
        malformed_result_count=malformed,
    )


class AdzunaMarketSearchClient:
    """Async adapter that keeps credentials and raw payloads inside the boundary."""

    def __init__(
        self,
        *,
        app_id: str,
        app_key: str,
        base_url: str,
        timeout_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not app_id.strip() or not app_key.strip():
            raise MarketConfigurationError(
                "ADZUNA_APP_ID and ADZUNA_APP_KEY are required for market retrieval"
            )
        self._app_id = app_id
        self._app_key = app_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._transport = transport
        self._client: httpx.AsyncClient | None = None

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(base_url={self._base_url!r}, "
            "app_id=<redacted>, app_key=<redacted>)"
        )

    @classmethod
    def from_settings(cls, settings: Settings) -> "AdzunaMarketSearchClient":
        if settings.adzuna_app_id is None or settings.adzuna_app_key is None:
            raise MarketConfigurationError(
                "ADZUNA_APP_ID and ADZUNA_APP_KEY are required for market retrieval"
            )
        return cls(
            app_id=settings.adzuna_app_id.get_secret_value(),
            app_key=settings.adzuna_app_key.get_secret_value(),
            base_url=settings.adzuna_base_url,
            timeout_seconds=settings.market_timeout_seconds,
        )

    async def __aenter__(self) -> Self:
        self._client = httpx.AsyncClient(
            timeout=self._timeout,
            transport=self._transport,
            headers={"Accept": "application/json"},
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._client is not None:
            await self._client.aclose()
        self._client = None

    async def search_page(self, request: StructuredJobSearchRequest) -> StructuredJobSearchPage:
        if self._client is None:
            raise MarketConfigurationError("Adzuna client must be used as an async context manager")
        endpoint = f"{self._base_url}/jobs/{request.country}/search/{request.page}"
        params: dict[str, Any] = {
            "app_id": self._app_id,
            "app_key": self._app_key,
            "results_per_page": request.results_per_page,
            "what": request.title,
            "where": request.location,
            "content-type": "application/json",
        }
        try:
            response = await self._client.get(endpoint, params=params)
            if response.status_code in {401, 403}:
                raise MarketAuthenticationError("Adzuna authentication failed")
            if response.status_code == 429:
                raise MarketRateLimitError("Adzuna rate limit reached")
            response.raise_for_status()
            try:
                payload = response.json()
            except ValueError as error:
                raise MarketContentError("Adzuna returned malformed JSON") from error
            return normalize_adzuna_payload(payload, page=request.page)
        except (MarketAuthenticationError, MarketRateLimitError, MarketContentError):
            raise
        except httpx.TimeoutException as error:
            raise MarketTimeoutError("Adzuna request timed out") from error
        except httpx.HTTPError as error:
            raise MarketTransportError("Adzuna is temporarily unavailable") from error
