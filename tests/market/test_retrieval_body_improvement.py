"""Realistic snippet-to-body regressions; no provider calls."""

import asyncio

import pytest

from ai_career_navigator.domain import GeographyScope
from ai_career_navigator.market.adzuna_client import normalize_adzuna_payload
from ai_career_navigator.market.combined_service import _enrich, _primary_evidence
from ai_career_navigator.market.currentness import currentness_rejection
from ai_career_navigator.market.mcp.fake_client import FakeMarketSearchClient
from ai_career_navigator.market.schemas import MarketPageContent

from .test_reliability_retrieval import NOW, structured


def evidence(**changes):
    return _primary_evidence(
        structured(description="Original brief excerpt.", **changes),
        goal_geography="Toronto, Canada",
        requested_scope=GeographyScope.STRICT_CITY,
        retrieved_at=NOW,
        thin_description_characters=500,
        target_role="Senior Java Developer",
        target_seniority="Senior",
    )


def enrich(page, *, original=None):
    original = original or evidence()
    client = FakeMarketSearchClient(content_outcomes={str(original.primary_source.url): page})
    return asyncio.run(_enrich(original, client))


def test_adzuna_contract_marks_even_long_search_description_as_excerpt():
    page = normalize_adzuna_payload(
        {
            "results": [
                {
                    "id": "123",
                    "title": "Senior Java Developer",
                    "redirect_url": "https://adzuna.ca/jobs/land/ad/123",
                    "description": "Source excerpt " * 100,
                    "company": {"display_name": "Employer"},
                    "location": {"display_name": "Toronto, Canada"},
                    "created": "2026-09-01",
                }
            ]
        },
        page=1,
    )
    item = page.results[0]
    assert item.content_complete is False
    result = _primary_evidence(
        item,
        goal_geography="Toronto, Canada",
        requested_scope=GeographyScope.STRICT_CITY,
        retrieved_at=NOW,
        thin_description_characters=500,
        target_role="Senior Java Developer",
        target_seniority="Senior",
    )
    assert result.enrichment_status.value == "NOT_ATTEMPTED"
    assert result.content_quality.value == "SHORT_EXCERPT"


def test_missing_identity_and_unchanged_snippet_do_not_count_as_completion():
    original = evidence()
    missing = MarketPageContent(url=str(original.primary_source.url), markdown="Welcome careers")
    assert enrich(missing).enrichment_reason == "TITLE_NOT_GROUNDED"
    unchanged = missing.model_copy(
        update={
            "title": original.posting.original_title,
            "markdown": original.primary_content.markdown,
        }
    )
    result = enrich(unchanged)
    assert result.enrichment_status.value == "FAILED"
    assert result.enrichment_reason == "NO_ADDITIONAL_CONTENT"


def test_one_selected_body_preserves_structured_identity_and_original_excerpt():
    original = evidence(requisition_id="123")
    body = "# Senior Java Developer\n## Requirements\nJava production experience.\n" * 15
    page = MarketPageContent(
        url="https://jobs.employer.example/jobs/123",
        title=original.posting.original_title,
        employer="Employer",
        location="Toronto, Canada",
        markdown=body,
        content_complete=True,
        closing_date="2026-10-01",
        requisition_id="123",
    )
    result = enrich(page, original=original)
    assert result.enrichment_status.value == "APPLIED"
    assert result.primary_content.markdown == body
    assert result.primary_source == original.primary_source
    assert result.posting.employer == original.posting.employer
    assert result.primary_content.closing_date == "2026-10-01"
    assert result.selected_content_source.value == "YOU"
    assert result.content_quality.value == "FULL_POSTING"
    assert result.supporting_contents[0] == original.primary_content
    assert str(result.supporting_sources[0].url) == page.url


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("employer", "Different Employer", "EMPLOYER_CONFLICT"),
        ("location", "Vancouver, British Columbia", "LOCATION_CONFLICT"),
    ],
)
def test_footer_mentions_cannot_override_conflicting_job_metadata(field, value, reason):
    page = MarketPageContent(
        url="https://jobs.other.example/jobs/123",
        title="Senior Java Developer",
        employer="Employer",
        location="Toronto, Canada",
        markdown="Senior Java Developer. Our partners include Employer, Toronto, Canada.",
    ).model_copy(update={field: value})
    assert enrich(page).enrichment_reason == reason


def test_different_returned_url_requires_vacancy_identity_not_just_matching_fields():
    page = MarketPageContent(
        url="https://different.example/careers",
        title="Senior Java Developer",
        markdown="Senior Java Developer job opportunities.",
    )
    assert enrich(page).enrichment_reason == "VACANCY_IDENTITY_UNCONFIRMED"
    remote = page.model_copy(update={"employer": "Employer", "location": "Remote"})
    assert enrich(remote).enrichment_reason == "VACANCY_IDENTITY_UNCONFIRMED"
    same_fields = page.model_copy(
        update={
            "employer": "Employer",
            "location": "Toronto, Canada",
            "markdown": "Senior Java Developer. Employer. Toronto, Canada. Qualifications: Java. "
            * 20,
        }
    )
    result = enrich(same_fields)
    assert result.enrichment_reason == "VACANCY_IDENTITY_UNCONFIRMED"
    assert result.primary_content.markdown == "Original brief excerpt."


def test_javascript_shell_does_not_replace_source_description():
    original = evidence()
    page = MarketPageContent(
        url=str(original.primary_source.url),
        title=original.posting.original_title,
        markdown="Senior Java Developer. Enable JavaScript to view this job.",
    )
    result = enrich(page, original=original)
    assert result.enrichment_reason == "BLOCKED_CONTENT"
    assert result.primary_content == original.primary_content


def test_clipped_body_is_never_labelled_complete():
    original = evidence()
    page = MarketPageContent(
        url=str(original.primary_source.url),
        title=original.posting.original_title,
        markdown="Requirements and responsibilities " * 2000,
        content_complete=True,
    )
    result = enrich(page)
    assert len(result.primary_content.markdown) == 40_000
    assert result.primary_content.content_complete is False
    assert result.content_quality.value == "SHORT_EXCERPT"


@pytest.mark.parametrize(
    "title,body",
    [
        ("Jobs at Employer", "The job you are looking for is no longer open.\n# Current openings"),
        ("404 | Employer Careers", "Suggested jobs: Senior Java Developer in Toronto"),
        ("Employer Careers", "# 404\n## Suggested jobs\nOther opportunities."),
    ],
)
def test_unavailable_posting_does_not_turn_suggested_jobs_into_original_vacancy(title, body):
    page = MarketPageContent(url="https://careers.example/jobs/1", title=title, markdown=body)
    assert currentness_rejection(page, as_of=NOW.date(), max_age_days=90)


def test_normal_live_job_body_is_not_rejected_for_unrelated_number():
    page = MarketPageContent(
        url="https://careers.example/jobs/1",
        title="Senior Java Developer",
        markdown="Responsibilities: investigate HTTP 404 errors in production services.",
    )
    assert currentness_rejection(page, as_of=NOW.date(), max_age_days=90) is None
