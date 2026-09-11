"""Conservative URL and posting deduplication."""

from collections.abc import Iterable
from difflib import SequenceMatcher
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


def deduplicate_postings(postings: Iterable[JobPosting]) -> tuple[list[JobPosting], int]:
    retained: list[JobPosting] = []
    duplicates = 0
    for posting in postings:
        retained_index = next(
            (index for index, prior in enumerate(retained) if same_vacancy(prior, posting)), None
        )
        if retained_index is None:
            retained.append(posting)
            continue
        duplicates += 1
        existing = retained[retained_index]
        group_id = existing.duplicate_group_id or uuid4()
        retained[retained_index] = existing.model_copy(update={"duplicate_group_id": group_id})
    return retained, duplicates


def same_vacancy(first: JobPosting, second: JobPosting) -> bool:
    """Merge only supported vacancy identities, not coincidentally similar titles."""
    if first.posting_id == second.posting_id:
        return True
    same_employer = bool(first.employer) and (
        normalize_employer(first.employer).casefold()
        == (normalize_employer(second.employer) or "").casefold()
    )
    if same_employer and first.requisition_id and second.requisition_id:
        return first.requisition_id.casefold() == second.requisition_id.casefold()
    if first.canonical_job_url and second.canonical_job_url:
        if canonicalize_url(first.canonical_job_url) == canonicalize_url(second.canonical_job_url):
            return True
    # Reused descriptions (even by the same employer) do not identify a vacancy.
    return False


def possible_duplicate(
    first: JobPosting, second: JobPosting, first_text: str, second_text: str
) -> bool:
    """Informational only: never use this result to merge records or transfer a JD."""
    employer = normalize_employer(first.employer)
    if (
        not employer
        or employer.casefold() != (normalize_employer(second.employer) or "").casefold()
    ):
        return False
    if same_vacancy(first, second):
        return False
    left = normalized_comparison(first_text)[:4000]
    right = normalized_comparison(second_text)[:4000]
    return min(len(left), len(right)) >= 100 and SequenceMatcher(None, left, right).ratio() >= 0.9
