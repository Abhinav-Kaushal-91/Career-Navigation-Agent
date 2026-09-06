"""Conservative URL and posting deduplication."""

from collections.abc import Iterable
from uuid import uuid4

from ai_career_navigator.domain import JobPosting
from ai_career_navigator.market.normalization import (
    canonicalize_url,
    normalize_employer,
    normalized_comparison,
)
from ai_career_navigator.market.schemas import MarketSearchResult


def deduplicate_search_results(
    results: Iterable[MarketSearchResult],
) -> tuple[list[MarketSearchResult], int]:
    retained: list[MarketSearchResult] = []
    seen: set[str] = set()
    duplicates = 0
    for result in results:
        canonical = canonicalize_url(result.url)
        if canonical is None:
            continue
        if canonical in seen:
            duplicates += 1
            continue
        seen.add(canonical)
        retained.append(result)
    return retained, duplicates


def _posting_key(posting: JobPosting) -> tuple[str, str, str] | None:
    employer = normalize_employer(posting.employer)
    if not employer:
        return None
    return (
        employer.casefold(),
        normalized_comparison(posting.normalized_title or posting.original_title),
        (posting.location or "").strip().casefold(),
    )


def deduplicate_postings(postings: Iterable[JobPosting]) -> tuple[list[JobPosting], int]:
    retained: list[JobPosting] = []
    index: dict[tuple[str, str, str], int] = {}
    duplicates = 0
    for posting in postings:
        key = _posting_key(posting)
        if key is None or key not in index:
            if key is not None:
                index[key] = len(retained)
            retained.append(posting)
            continue
        duplicates += 1
        retained_index = index[key]
        existing = retained[retained_index]
        group_id = existing.duplicate_group_id or uuid4()
        retained[retained_index] = existing.model_copy(update={"duplicate_group_id": group_id})
    return retained, duplicates
