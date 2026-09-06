"""Deterministic market client for tests and local service development."""

from collections import deque
from collections.abc import Iterable, Mapping
from types import TracebackType
from typing import Self

from ai_career_navigator.market.errors import MarketContentError
from ai_career_navigator.market.schemas import (
    MarketPageContent,
    MarketSearchRequest,
    MarketSearchResult,
)

SearchOutcome = list[MarketSearchResult] | Exception
ContentOutcome = MarketPageContent | Exception


class FakeMarketSearchClient:
    def __init__(
        self,
        *,
        search_outcomes: Iterable[SearchOutcome] = (),
        content_outcomes: Mapping[str, ContentOutcome] | None = None,
    ) -> None:
        self._search_outcomes = deque(search_outcomes)
        self._content_outcomes = dict(content_outcomes or {})
        self.search_calls: list[str] = []
        self.search_requests: list[MarketSearchRequest] = []
        self.content_calls: list[str] = []
        self.entered = False

    async def __aenter__(self) -> Self:
        self.entered = True
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.entered = False

    async def search(self, request: MarketSearchRequest) -> list[MarketSearchResult]:
        self.search_calls.append(request.query)
        self.search_requests.append(request)
        if not self._search_outcomes:
            return []
        outcome = self._search_outcomes.popleft()
        if isinstance(outcome, Exception):
            raise outcome
        return list(outcome)

    async def fetch_content(self, url: str) -> MarketPageContent:
        self.content_calls.append(url)
        outcome = self._content_outcomes.get(url)
        if outcome is None:
            raise MarketContentError("fake content response was not configured")
        if isinstance(outcome, Exception):
            raise outcome
        return outcome
