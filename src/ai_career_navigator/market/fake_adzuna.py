"""Deterministic structured market provider for offline tests."""

from collections import deque
from collections.abc import Iterable
from types import TracebackType
from typing import Self

from ai_career_navigator.market.schemas import (
    StructuredJobSearchPage,
    StructuredJobSearchRequest,
)

StructuredOutcome = StructuredJobSearchPage | Exception


class FakeAdzunaMarketSearchClient:
    def __init__(self, outcomes: Iterable[StructuredOutcome] = ()) -> None:
        self._outcomes = deque(outcomes)
        self.requests: list[StructuredJobSearchRequest] = []
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

    async def search_page(self, request: StructuredJobSearchRequest) -> StructuredJobSearchPage:
        self.requests.append(request)
        if not self._outcomes:
            return StructuredJobSearchPage(provider="ADZUNA", page=request.page)
        outcome = self._outcomes.popleft()
        if isinstance(outcome, Exception):
            raise outcome
        return outcome
