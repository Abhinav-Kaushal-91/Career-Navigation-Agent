from datetime import date

import pytest

from ai_career_navigator.domain import ConfidenceLevel, JobPosting
from ai_career_navigator.market.deduplication import (
    deduplicate_postings,
    deduplicate_search_results,
)
from ai_career_navigator.market.normalization import (
    canonicalize_url,
    create_job_posting,
    create_source_record,
    normalize_title,
    normalized_comparison,
)
from ai_career_navigator.market.schemas import MarketPageContent, MarketSearchResult
from ai_career_navigator.market.validation import (
    is_plausible_current_job_page,
    is_promising_search_result,
    is_url_like_title,
    observed_related_titles,
)

TARGET = "AI Solutions Architect"


def result(
    *,
    title: str = TARGET,
    url: str = "https://careers.example.com/jobs/123",
    snippet: str = "Apply now. Review the qualifications for this position.",
) -> MarketSearchResult:
    return MarketSearchResult(title=title, url=url, snippets=[snippet])


def page(**overrides: str) -> MarketPageContent:
    values = {
        "url": "https://careers.example.com/jobs/123",
        "title": TARGET,
        "markdown": "Job description. Responsibilities and qualifications. Apply now.",
        "employer": "Example Corp",
        "location": "Toronto, Canada",
    }
    values.update(overrides)
    return MarketPageContent(**values)


@pytest.mark.parametrize(
    ("title", "url", "snippet"),
    (
        (TARGET, "https://example.com/blog/ai-architect", "Blog article"),
        (TARGET, "https://example.com/salary", "AI Solutions Architect salary guide"),
        (TARGET, "https://example.com/course", "Online training course"),
        (TARGET, "https://example.com/resume", "Resume template and examples"),
        ("Registered Nurse", "https://example.com/jobs/1", "Apply now"),
    ),
)
def test_obvious_non_job_results_are_rejected(title: str, url: str, snippet: str) -> None:
    assert not is_promising_search_result(result(title=title, url=url, snippet=snippet), TARGET)


def test_plausible_current_job_result_and_page_are_accepted() -> None:
    candidate = result()

    assert is_promising_search_result(candidate, TARGET)
    assert is_plausible_current_job_page(candidate, page(), TARGET)


def test_expired_job_page_is_rejected() -> None:
    assert not is_plausible_current_job_page(
        result(),
        page(markdown="This job posting is closed. Responsibilities and qualifications."),
        TARGET,
    )


def test_title_normalization_is_lightweight() -> None:
    assert normalize_title(" Sr. AI Solutions Architect ") == "Senior AI Solutions Architect"
    assert normalize_title("AI Solution Architect") != normalize_title("AI Solutions Architect")
    assert normalized_comparison("Sr. AI Solutions Architect") == (
        normalized_comparison("Senior AI Solution Architect")
    )


def test_url_and_search_titles_are_not_related_title_expansion_candidates() -> None:
    titles = [
        "AI Platform Architect",
        "31 AI Solutions Architect Jobs in Canada",
        "www.example.com/Jobs/AI-Solutions-Architect/in-Toronto",
        "AI Solutions Architect Job Search Results",
    ]

    assert observed_related_titles(titles, TARGET, limit=5) == ["AI Platform Architect"]
    assert is_url_like_title("https://example.com/jobs/123")
    assert is_url_like_title("/Jobs/AI-Solutions-Architect")


def test_canonical_url_removes_only_tracking_noise() -> None:
    url = "https://Careers.Example.com/jobs/123/?utm_source=test&job=123#details"

    assert canonicalize_url(url) == "https://careers.example.com/jobs/123?job=123"


def test_source_and_posting_mapping_leave_missing_optional_fields_unknown() -> None:
    candidate = result()
    content = page(employer="", location="")
    source = create_source_record(candidate, retrieval_date=date(2026, 9, 3), page=content)
    posting = create_job_posting(candidate, content, source)

    assert source.url.host == "careers.example.com"
    assert source.employer is None
    assert posting.employer is None
    assert posting.posting_date is None
    assert posting.extraction_confidence is ConfidenceLevel.HIGH


def test_identical_canonical_urls_are_deduplicated() -> None:
    first = result(url="https://example.com/jobs/1?utm_source=a")
    second = result(url="https://example.com/jobs/1?utm_source=b")

    retained, duplicate_count = deduplicate_search_results([first, second])

    assert retained == [first]
    assert duplicate_count == 1


def test_same_employer_title_and_location_are_grouped() -> None:
    common = {
        "source_id": create_source_record(result(), retrieval_date=date(2026, 9, 3)).source_id,
        "original_title": TARGET,
        "normalized_title": TARGET,
        "employer": "Example Corp",
        "location": "Toronto",
        "extraction_confidence": ConfidenceLevel.HIGH,
    }
    first = JobPosting(**common)
    second = JobPosting(
        **{
            **common,
            "source_id": create_source_record(
                result(url="https://example.com/jobs/2"), retrieval_date=date(2026, 9, 3)
            ).source_id,
        }
    )

    retained, duplicate_count = deduplicate_postings([first, second])

    assert len(retained) == 1
    assert retained[0].duplicate_group_id is not None
    assert duplicate_count == 1
