"""Completion resolves real vacancy identity without losing source provenance."""

import asyncio

import pytest

from ai_career_navigator.market import FakeAdzunaMarketSearchClient
from ai_career_navigator.market.combined_service import retrieve_combined_market
from ai_career_navigator.market.mcp.fake_client import FakeMarketSearchClient
from ai_career_navigator.market.schemas import (
    MarketPageContent,
    MarketSourceProvider,
    SearchLimits,
    StructuredJobSearchPage,
)

from .test_reliability_retrieval import NOW, goal, structured


def _run_completion(*, requisitions=("REQ-42", "REQ-42"), first_changes=None):
    jobs = [
        structured(
            index,
            url=f"https://www.adzuna.ca/details/{index + 1000}",
            content_complete=False,
            # Distinct excerpts must not be merged before their identity is resolved.
            description=f"Search excerpt {index}. Requirements: Java delivery experience required.",
        )
        for index in range(2)
    ]
    canonical_url = "https://careers.employer.example/jobs/REQ-42"
    body = (
        "Senior Java Developer. Employer. Toronto, Canada.\n"
        "Responsibilities: Develop reliable Java services and review technical designs.\n"
        "Qualifications: Java development and automated testing experience required.\n"
    ) * 4
    pages = [
        MarketPageContent(
            url=canonical_url,
            canonical_job_url=canonical_url,
            requisition_id=requisitions[index],
            title=job.title,
            employer=job.company,
            location=job.location,
            markdown=body,
            content_complete=True,
        )
        for index, job in enumerate(jobs)
    ]
    if first_changes:
        pages[0] = pages[0].model_copy(update=first_changes)
    primary = FakeAdzunaMarketSearchClient(
        [StructuredJobSearchPage(provider="ADZUNA", page=1, results=jobs)]
    )
    support = FakeMarketSearchClient(
        search_outcomes=[[], [], []],
        content_outcomes={job.url: page for job, page in zip(jobs, pages, strict=True)},
    )
    result = asyncio.run(
        retrieve_combined_market(
            goal(),
            primary,
            enrichment_client=support,
            limits=SearchLimits(
                max_variant_queries=0,
                max_enrichments=2,
                max_content_fetches=4,
                max_retries=0,
            ),
            max_pages=1,
            now=NOW,
        )
    )
    return result, support, jobs


def test_two_structured_redirects_resolving_one_vacancy_keep_both_discovery_sources():
    result, support, jobs = _run_completion()

    assert support.content_calls == [job.url for job in jobs]
    assert result.enrichment_attempt_count == 2
    assert result.snapshot.validated_posting_count == 1
    assert result.snapshot.distinct_employer_count == 1
    assert result.snapshot.employer_posting_counts == {"Employer": 1}
    assert result.snapshot.duplicate_posting_count == 1
    assert len(result.postings) == len(result.posting_evidence) == 1
    evidence = result.posting_evidence[0]
    assert evidence.posting.canonical_job_url == "https://careers.employer.example/jobs/REQ-42"
    assert evidence.posting.requisition_id == "REQ-42"
    assert evidence.selected_content_source is MarketSourceProvider.YOU
    provenance = [evidence.primary_source, *evidence.supporting_sources]
    structured_sources = [item for item in provenance if item.source_type == "ADZUNA"]
    assert {str(item.url) for item in structured_sources} == {job.url for job in jobs}
    assert len({item.source_id for item in structured_sources}) == 2
    assert any(item.source_type == "YOU" for item in provenance)
    retained_text = " ".join(item.markdown for item in evidence.supporting_contents)
    assert all(job.description in retained_text for job in jobs)
    posting_audits = [item for item in result.posting_audits if item.posting_id]
    assert len(posting_audits) == 2
    assert sum(item.duplicate_of is not None for item in posting_audits) == 1


def test_different_resolved_requisitions_remain_distinct_even_with_same_url_and_body():
    result, support, jobs = _run_completion(requisitions=("REQ-42", "REQ-43"))

    assert support.content_calls == [job.url for job in jobs]
    assert result.snapshot.validated_posting_count == 2
    assert result.snapshot.distinct_employer_count == 1
    assert result.snapshot.employer_posting_counts == {"Employer": 2}
    assert result.snapshot.duplicate_posting_count == 0
    assert {item.requisition_id for item in result.postings} == {"REQ-42", "REQ-43"}
    assert all(item.duplicate_of is None for item in result.posting_audits)


@pytest.mark.parametrize(
    "closed_changes",
    [
        {"active_status": "CLOSED"},
        {"closing_date": "2026-09-05"},
    ],
)
def test_closed_vacancy_discovered_during_enrichment_is_removed_before_dedup(closed_changes):
    result, support, jobs = _run_completion(
        requisitions=("REQ-closed", "REQ-open"), first_changes=closed_changes
    )

    assert support.content_calls == [job.url for job in jobs]
    assert result.enrichment_attempt_count == 2
    assert result.snapshot.validated_posting_count == 1
    assert result.snapshot.distinct_employer_count == 1
    assert result.postings[0].requisition_id == "REQ-open"
    assert result.rejected_candidate_count >= 1
    currentness_audits = [
        item for item in result.posting_audits if item.stage == "CURRENTNESS_AFTER_ENRICHMENT"
    ]
    assert len(currentness_audits) == 1
    assert currentness_audits[0].source_url == jobs[0].url
    assert currentness_audits[0].rejection_reason
    assert currentness_audits[0].posting_id != str(result.postings[0].posting_id)
