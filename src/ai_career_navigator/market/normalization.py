"""Conservative normalization from candidate evidence into domain records."""

import re
from datetime import UTC, date, datetime
from hashlib import sha256
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import ValidationError

from ai_career_navigator.domain import ConfidenceLevel, JobPosting, SourceRecord
from ai_career_navigator.market.schemas import MarketPageContent, MarketSearchResult, ValidatedUrl

TRACKING_PARAMETERS = {"fbclid", "gclid", "ref", "source"}


def normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def normalize_title(value: str) -> str:
    title = normalize_whitespace(value)
    title = re.sub(r"\bSr(?:\.|\b)", "Senior", title, flags=re.IGNORECASE)
    title = re.sub(r"\bJr(?:\.|\b)", "Junior", title, flags=re.IGNORECASE)
    return title.strip(" |-–—")


def normalized_comparison(value: str) -> str:
    tokens = re.findall(r"[a-z0-9]+", normalize_title(value).casefold())
    return " ".join("solution" if token == "solutions" else token for token in tokens)


def normalize_employer(value: str | None) -> str | None:
    if not value:
        return None
    normalized = normalize_whitespace(value).strip(" |-–—")
    return normalized or None


def canonicalize_url(value: str) -> str | None:
    try:
        validated = str(ValidatedUrl(url=value).url)
    except ValidationError:
        return None
    parts = urlsplit(validated)
    query = [
        (key, item)
        for key, item in parse_qsl(parts.query, keep_blank_values=True)
        if not key.casefold().startswith("utm_") and key.casefold() not in TRACKING_PARAMETERS
    ]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit(
        (parts.scheme.casefold(), parts.netloc.casefold(), path, urlencode(query), "")
    )


def source_domain(url: str) -> str | None:
    canonical = canonicalize_url(url)
    return urlsplit(canonical).netloc.removeprefix("www.") if canonical else None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def create_source_record(
    candidate: MarketSearchResult,
    *,
    retrieval_date: date,
    page: MarketPageContent | None = None,
    accessible: bool = True,
    limitations: list[str] | None = None,
) -> SourceRecord:
    canonical = canonicalize_url(candidate.url)
    if canonical is None:
        raise ValueError("candidate source URL is invalid")
    return SourceRecord(
        source_type="CURRENT_JOB_POSTING",
        title=normalize_title(page.title or candidate.title)
        if page
        else normalize_title(candidate.title),
        url=canonical,
        employer=normalize_employer(page.employer) if page else None,
        geography=normalize_whitespace(page.location) if page and page.location else None,
        retrieval_date=retrieval_date,
        publication_date=_parse_date(page.posting_date) if page else None,
        accessible=accessible,
        limitations=limitations or [],
    )


def create_job_posting(
    candidate: MarketSearchResult,
    page: MarketPageContent,
    source: SourceRecord,
    *,
    retrieved_at: datetime | None = None,
) -> JobPosting:
    original_title = normalize_whitespace(page.title or candidate.title)
    return JobPosting(
        source_id=source.source_id,
        original_title=original_title,
        normalized_title=normalize_title(original_title),
        employer=normalize_employer(page.employer),
        location=normalize_whitespace(page.location) if page.location else None,
        work_mode=normalize_whitespace(page.work_mode) if page.work_mode else None,
        employment_type=(
            normalize_whitespace(page.employment_type) if page.employment_type else None
        ),
        seniority=normalize_whitespace(page.seniority) if page.seniority else None,
        posting_date=_parse_date(page.posting_date),
        closing_date=_parse_date(page.closing_date),
        retrieved_at=retrieved_at or datetime.now(UTC),
        active_status=normalize_whitespace(page.active_status) if page.active_status else None,
        requisition_id=page.requisition_id,
        canonical_job_url=canonicalize_url(page.canonical_job_url or page.url),
        content_fingerprint=(
            sha256(normalize_whitespace(page.markdown).encode()).hexdigest()
            if len(page.markdown.strip()) >= 100
            else None
        ),
        discovered_at=retrieved_at or datetime.now(UTC),
        currentness_checked_at=retrieved_at or datetime.now(UTC),
        currentness_basis=(
            "EMPLOYER_VERIFIED_OPEN"
            if page.active_status == "VERIFIED_OPEN"
            else "RETRIEVED_PAGE_STATUS"
            if page.active_status
            else "UNKNOWN"
        ),
        extraction_confidence=ConfidenceLevel.HIGH if page.title else ConfidenceLevel.MODERATE,
    )
