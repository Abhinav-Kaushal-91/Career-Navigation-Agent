"""Offline contract checks for Adzuna-seeded You search and conservative identity."""

import asyncio

import pytest

from ai_career_navigator.market import FakeAdzunaMarketSearchClient
from ai_career_navigator.market.combined_service import retrieve_combined_market
from ai_career_navigator.market.deduplication import same_vacancy
from ai_career_navigator.market.mcp.fake_client import FakeMarketSearchClient
from ai_career_navigator.market.mcp.you_client import YouMcpMarketSearchClient
from ai_career_navigator.market.schemas import (
    EnrichmentStatus,
    MarketPageContent,
    MarketSearchRequest,
    MarketSearchResult,
    SearchLimits,
    SearchPassType,
    StructuredJobSearchPage,
)

from .test_reliability_retrieval import NOW, goal, retrieve, structured


class SeedClient(FakeMarketSearchClient):
    async def search(self, request):
        self.search_calls.append(request.query)
        self.search_requests.append(request)
        if request.pass_type is not SearchPassType.POSTING_ENRICHMENT:
            return []
        return [
            MarketSearchResult(title=page.title, url=url)
            for url, page in self._content_outcomes.items()
        ]


def seeded_run(
    *,
    role="Senior Java Developer",
    seed_title=None,
    matched=False,
    location="Toronto, Canada",
    url="https://careers.example/jobs/REQ-7",
    search_limit=12,
    fetch_limit=10,
):
    seed = structured(
        title=seed_title or role,
        content_complete=False,
        description="Short search excerpt.",
        requisition_id="REQ-7" if matched else None,
    )
    body = (
        f"{role} at Employer in {location}.\n"
        "Responsibilities: Design and deliver reliable solutions with business stakeholders.\n"
        "Qualifications: Relevant professional delivery experience is required. "
        "Collaborate across teams and document technical decisions.\n"
    ) * 4
    client = SeedClient(
        content_outcomes={
            url: MarketPageContent(
                url=url,
                title=role,
                employer="Employer",
                location=location,
                markdown=body,
                requisition_id="REQ-7",
                content_complete=True,
                posting_date="2026-09-01",
            )
        }
    )
    result = asyncio.run(
        retrieve_combined_market(
            goal(role),
            FakeAdzunaMarketSearchClient(
                [StructuredJobSearchPage(provider="ADZUNA", page=1, results=[seed])]
            ),
            enrichment_client=client,
            now=NOW,
            max_pages=1,
            limits=SearchLimits(
                max_variant_queries=0,
                max_enrichments=1,
                max_total_search_calls=search_limit,
                max_content_fetches=fetch_limit,
                max_retries=0,
            ),
        )
    )
    return result, client, seed


@pytest.mark.parametrize("role", ["Senior Java Developer", "Senior Financial Analyst"])
def test_other_vacancy_from_seed_is_added_without_attaching_jd_to_seed(role):
    result, client, seed = seeded_run(role=role)
    assert len(result.postings) == 2
    original = next(x for x in result.posting_evidence if x.primary_source.source_type == "ADZUNA")
    found = next(x for x in result.posting_evidence if x.primary_source.source_type == "YOU")
    assert original.primary_content.markdown == seed.description
    assert original.enrichment_status is EnrichmentStatus.FAILED
    assert found.discovery_seed_posting_ids == [str(original.posting.posting_id)]
    assert found.content_quality.value == "FULL_POSTING"
    assert result.snapshot.distinct_employer_count == 1
    requests = [
        r for r in client.search_requests if r.pass_type is SearchPassType.POSTING_ENRICHMENT
    ]
    assert len(requests) == 1
    assert f'"{seed.company}"' in requests[0].query
    assert seed.title in requests[0].query and seed.location in requests[0].query
    assert requests[0].full_page and requests[0].crawl_timeout_seconds == 60
    assert result.you_search_count == len(client.search_calls)
    assert result.snapshot.content_fetch_count == len(client.content_calls)


def test_verified_shared_requisition_merges_sources_and_uses_full_jd():
    result, _, _ = seeded_run(matched=True)
    assert len(result.postings) == 1
    assert result.cross_source_match_count == 1
    assert result.enrichment_success_count == 1
    record = result.posting_evidence[0]
    assert record.content_quality.value == "FULL_POSTING"
    assert {s.source_type for s in [record.primary_source, *record.supporting_sources]} == {
        "ADZUNA",
        "YOU",
    }


def test_related_seed_is_kept_and_attempted_without_becoming_exact():
    result, client, _ = seeded_run(seed_title="Junior Java Developer")
    assert result.snapshot.related_title_count == 1
    assert any("Junior Java Developer" in r.query for r in client.search_requests)
    audit = next(a for a in result.posting_audits if a.title == "Junior Java Developer")
    assert not audit.selected_for_primary_evidence


def test_out_of_scope_new_vacancy_does_not_inherit_seed_location():
    result, _, _ = seeded_run(location="Vancouver, British Columbia, Canada")
    assert len(result.postings) == 1
    assert result.posting_evidence[0].primary_source.source_type == "ADZUNA"
    assert any(
        a.rejection_reason and "Geography" in a.rejection_reason for a in result.posting_audits
    )


def test_seed_search_respects_shared_limits_without_claiming_unavailable_jd():
    result, client, _ = seeded_run(search_limit=2, fetch_limit=1)
    assert len(client.search_calls) + result.primary_search_count <= 2
    assert len(client.content_calls) <= 1
    assert result.posting_evidence[0].enrichment_deferred_reason == "SEED_SEARCH_BUDGET_EXHAUSTED"


@pytest.mark.parametrize(
    "url",
    [
        "https://www.linkedin.com/jobs/view/senior-java-developer-4451905067",
        "https://www.glassdoor.com/job-listing/senior-java-developer.htm?jl=1234",
        "https://www.ziprecruiter.com/c/Employer/Job/Senior-Java-Developer?jid=1234",
    ],
)
def test_individual_job_board_copy_is_retained_but_not_called_employer_source(url):
    result, _, _ = seeded_run(url=url)
    assert len(result.postings) == 2
    found = next(x for x in result.posting_evidence if x.primary_source.source_type == "YOU")
    assert found.source_type.value == "INDIVIDUAL_JOB_BOARD_POSTING"


def test_identical_text_across_employers_does_not_merge_or_flag():
    result = retrieve(structured(1, company="First"), structured(2, company="Second"))
    assert len(result.postings) == 2
    assert not same_vacancy(*result.postings)
    assert all(not item.possible_duplicate_posting_ids for item in result.posting_evidence)


def test_full_page_markdown_is_requested_and_cached_without_cross_result_assignment():
    client = YouMcpMarketSearchClient(
        endpoint="https://example.com/mcp", api_key="test", timeout_seconds=60
    )
    client._search_properties = {"query", "extraction", "crawl_timeout", "count"}
    client._search_parameter_schemas = {"extraction": {"type": "object"}}
    calls = []
    first, second = "https://employer.example/jobs/1", "https://employer.example/jobs/2"

    async def call(tool, arguments):
        calls.append((tool, arguments))
        if tool == "you-search":
            return {
                "results": {
                    "web": [
                        {
                            "url": first,
                            "title": "First job",
                            "contents": {"markdown": "First job body"},
                        },
                        {"url": second, "title": "Second job", "snippets": ["Only a snippet"]},
                    ]
                }
            }
        return {"url": second, "markdown": "Second job body"}

    client._call = call

    async def run():
        await client.search(
            MarketSearchRequest(
                query="example",
                pass_type="POSTING_ENRICHMENT",
                freshness="year",
                full_page=True,
                count=3,
            )
        )
        assert (await client.fetch_content(first)).markdown == "First job body"
        assert (await client.fetch_content(second)).markdown == "Second job body"

    asyncio.run(run())
    assert calls[0][1]["extraction"] == {
        "extraction_mode": "full_page",
        "full_page": {"extraction_formats": ["markdown"]},
    }
    assert calls[0][1]["crawl_timeout"] == 60
    assert len(calls) == 2  # Second result needs its own content fetch.
