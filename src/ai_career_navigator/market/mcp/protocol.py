"""Provider-independent market-search client contract."""

from types import TracebackType
from typing import Protocol, Self

from ai_career_navigator.market.schemas import (
    MarketPageContent,
    MarketSearchRequest,
    MarketSearchResult,
    StructuredJobSearchPage,
    StructuredJobSearchRequest,
)


class MarketSearchClient(Protocol):
    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def search(self, request: MarketSearchRequest) -> list[MarketSearchResult]: ...

    async def fetch_content(self, url: str) -> MarketPageContent: ...


class StructuredJobSearchClient(Protocol):
    """Provider boundary for APIs returning one structured record per posting."""

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def search_page(self, request: StructuredJobSearchRequest) -> StructuredJobSearchPage: ...
