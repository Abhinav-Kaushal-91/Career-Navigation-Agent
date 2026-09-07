import asyncio

import pytest

from ai_career_navigator.config import Settings
from ai_career_navigator.market import (
    FakeAdzunaMarketSearchClient,
    MarketContentError,
    analyze_market_requirements,
)
from ai_career_navigator.market.combined_service import _content_quality, retrieve_combined_market
from ai_career_navigator.market.mcp.fake_client import FakeMarketSearchClient
from ai_career_navigator.market.schemas import (
    MarketPageContent,
    SearchLimits,
    StructuredJobSearchPage,
)
from ai_career_navigator.market.service import limits_from_settings

from .test_reliability_retrieval import NOW, goal, structured
from .test_requirement_processing import (
    GEOGRAPHY,
    TARGET,
    extraction,
    gateway,
    requirement,
    source_content,
)


def run_completion(*, override=None, configured=None, fetch_limit=12, analyze_limit=5):
    jobs = [
        structured(index, company=f"Employer {index}", description="Requirements: Java required.")
        for index in range(6)
    ]
    primary = FakeAdzunaMarketSearchClient(
        [StructuredJobSearchPage(provider="ADZUNA", page=1, results=jobs)]
    )
    contents = {
        job.url: MarketPageContent(
            url=job.url, title="Unrelated Role", markdown="Unrelated responsibilities."
        )
        for job in jobs
    }
    contents[jobs[0].url] = MarketContentError("Private transport detail must not appear")
    you = FakeMarketSearchClient(search_outcomes=[[], [], []], content_outcomes=contents)
    result = asyncio.run(
        retrieve_combined_market(
            goal(),
            primary,
            enrichment_client=you,
            max_pages=1,
            max_enrichments=override,
            now=NOW,
            limits=SearchLimits(
                max_variant_queries=0,
                max_content_fetches=fetch_limit,
                analysis_posting_limit=analyze_limit,
                max_enrichments=configured,
            ),
        )
    )
    return result, you


@pytest.mark.parametrize(
    "override,configured,expected", [(None, None, 5), (2, None, 2), (None, 2, 2)]
)
def test_completion_budget_follows_analyzed_cohort_and_preserves_explicit_two(
    override, configured, expected
):
    result, you = run_completion(override=override, configured=configured)
    assert result.enrichment_attempt_count == expected
    assert len(you.content_calls) == expected
    assert result.snapshot.content_fetch_count == expected
    assert len(you.search_requests) == 3
    assert result.enrichment_success_count == 0
    statuses = [audit.enrichment_status for audit in result.posting_audits if audit.posting_id]
    assert (
        sum(
            status is not None and status.value in {"FAILED", "CONFLICT_REJECTED"}
            for status in statuses
        )
        == expected
    )
    deferred = [audit for audit in result.posting_audits if audit.enrichment_deferred_reason]
    assert len(deferred) == 6 - expected
    assert all(
        item.enrichment_deferred_reason == "ENRICHMENT_BUDGET_EXHAUSTED" for item in deferred
    )
    conflicts = [
        audit for audit in result.posting_audits if audit.enrichment_reason == "TITLE_NOT_GROUNDED"
    ]
    assert conflicts
    assert all(
        item.enrichment_target_url and item.content_quality.value == "SHORT_EXCERPT"
        for item in conflicts
    )
    failures = [audit for audit in result.posting_audits if audit.enrichment_failure_category]
    assert failures[0].enrichment_failure_category == "MarketContentError"
    assert "Private transport" not in result.model_dump_json()


def test_completion_never_exceeds_shared_fetch_budget():
    result, you = run_completion(fetch_limit=2)
    assert result.enrichment_attempt_count == len(you.content_calls) == 2
    assert result.snapshot.content_fetch_count <= 2


def test_completion_prioritizes_primary_seniority_and_distinct_employers():
    jobs = [
        structured(
            0,
            title="Junior Java Developer",
            company="Junior Employer",
            description="Requirements: Java required.",
        ),
        structured(
            1, company="Employer A", requisition_id="A1", description="Requirements: Java required."
        ),
        structured(
            2, company="Employer A", requisition_id="A2", description="Requirements: Java required."
        ),
        structured(3, company="Employer B", description="Requirements: Java required."),
    ]
    primary = FakeAdzunaMarketSearchClient(
        [StructuredJobSearchPage(provider="ADZUNA", page=1, results=jobs)]
    )
    you = FakeMarketSearchClient(search_outcomes=[[], [], []])
    result = asyncio.run(
        retrieve_combined_market(
            goal(),
            primary,
            enrichment_client=you,
            max_pages=1,
            max_enrichments=2,
            now=NOW,
            limits=SearchLimits(max_variant_queries=0),
        )
    )
    assert you.content_calls == [jobs[1].url, jobs[3].url]
    assert result.enrichment_attempt_count == 2
    assert all("markdown" not in audit.model_dump() for audit in result.posting_audits)


def test_production_completion_budget_is_explicit_and_derived_from_settings():
    default = limits_from_settings(Settings(_env_file=None, market_analysis_posting_limit=5))
    assert default.analysis_posting_limit == 5
    assert default.max_enrichments is None
    explicit = limits_from_settings(Settings(_env_file=None, market_max_enrichments=2))
    assert explicit.max_enrichments == 2


def test_long_content_does_not_claim_complete_without_explicit_completeness_metadata():
    page = MarketPageContent(url="https://example.test/jobs/1", markdown="Qualifications " * 100)
    assert _content_quality(page).value == "UNKNOWN"
    assert (
        _content_quality(page.model_copy(update={"content_complete": True})).value == "FULL_POSTING"
    )
    assert (
        _content_quality(page.model_copy(update={"content_complete": False})).value
        == "SHORT_EXCERPT"
    )


def test_grounding_failed_response_does_not_dilute_valid_frequency_denominator():
    sources = [
        source_content(
            "Requirements: Java required.",
            page_title=TARGET,
            employer=f"Employer {index}",
            location=GEOGRAPHY,
            url=f"https://jobs.example/jobs/{index}",
        )
        for index in range(2)
    ]
    model_gateway, provider = gateway(
        extraction(requirement("Invented Python required", "Python")),
        extraction(requirement("Java required", "Java")),
    )
    result = analyze_market_requirements(
        sources,
        target_role=TARGET,
        geography=GEOGRAPHY,
        model_gateway=model_gateway,
        enable_target_variant_expansion=False,
    )
    assert len(provider.calls) == 2
    assert result.summary.schema_valid_extraction_count == 2
    assert result.summary.analyzed_posting_count == 1
    assert result.summary.postings_with_accepted_hiring_requirements == 1
    assert result.summary.rejected_grounding_item_count == 1
    assert result.summary.requirements[0].combined_frequency == 1.0
    assert result.posting_audits[0].extraction_status.value == "GROUNDING_FAILED"


def test_legitimate_empty_response_is_not_the_same_as_grounding_failure():
    source = source_content(
        "Job description. Join our team. Apply now.",
        page_title=TARGET,
        employer="Employer",
        location=GEOGRAPHY,
        url="https://jobs.example/jobs/empty",
    )
    model_gateway, provider = gateway(extraction())
    result = analyze_market_requirements(
        [source],
        target_role=TARGET,
        geography=GEOGRAPHY,
        model_gateway=model_gateway,
        enable_target_variant_expansion=False,
    )
    assert len(provider.calls) == 1
    assert (
        result.summary.schema_valid_extraction_count == result.summary.analyzed_posting_count == 1
    )
    assert result.summary.postings_with_accepted_hiring_requirements == 0
    assert result.summary.rejected_grounding_item_count == 0
    assert result.posting_audits[0].extraction_status.value == "SUCCEEDED"
    assert any("does not establish" in text for text in result.summary.limitations)
