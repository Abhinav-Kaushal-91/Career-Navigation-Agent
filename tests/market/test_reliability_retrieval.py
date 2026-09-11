"""Frozen correctness checks for V1 retrieval, with no network calls."""

import asyncio
from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from ai_career_navigator.domain import (
    ApprovalStatus,
    CareerGoal,
    ConfidenceLevel,
    GoalType,
    JobPosting,
)
from ai_career_navigator.market import FakeAdzunaMarketSearchClient
from ai_career_navigator.market.combined_service import (
    _content_score,
    _failed_structured_pass,
    _merge_duplicate_evidence,
    retrieve_combined_market,
)
from ai_career_navigator.market.currentness import currentness_rejection
from ai_career_navigator.market.deduplication import deduplicate_postings
from ai_career_navigator.market.mcp.fake_client import FakeMarketSearchClient
from ai_career_navigator.market.mcp.you_client import (
    YouMcpMarketSearchClient,
    normalize_you_content_payload,
)
from ai_career_navigator.market.processing import assess_title
from ai_career_navigator.market.schemas import (
    MarketPageContent,
    MarketSearchResult,
    MarketSourceProvider,
    SearchLimits,
    StructuredJobResult,
    StructuredJobSearchPage,
    StructuredJobSearchRequest,
)
from ai_career_navigator.market.search_plan import build_search_plan, build_you_query_family
from ai_career_navigator.market.service import retrieve_current_market
from ai_career_navigator.market.validation import is_promising_search_result

NOW = datetime(2026, 9, 6, tzinfo=UTC)


def goal(role="Senior Java Developer"):
    return CareerGoal(
        goal_type=GoalType.TARGET_CAREER_PATH,
        target_role=role,
        target_location="Toronto, Canada",
        approval_status=ApprovalStatus.APPROVED,
        approved_at=NOW,
    )


def structured(index=1, **changes):
    values = dict(
        provider=MarketSourceProvider.ADZUNA,
        provider_job_id=str(index),
        title="Senior Java Developer",
        url=f"https://employer.example/jobs/{index}",
        company="Employer",
        location="Toronto, Canada",
        description=(
            "We seek a Senior Java Developer. Required skills include Spring Boot and Cloud. "
        )
        * 10,
        created=date(2026, 9, 1),
    )
    values.update(changes)
    return StructuredJobResult(**values)


def retrieve(*jobs, **options):
    client = FakeAdzunaMarketSearchClient(
        [StructuredJobSearchPage(provider=MarketSourceProvider.ADZUNA, page=1, results=list(jobs))]
    )
    return asyncio.run(
        retrieve_combined_market(
            goal(),
            client,
            now=NOW,
            max_pages=1,
            limits=SearchLimits(max_variant_queries=0, **options),
        )
    )


def test_structured_query_audit_retains_parameters_without_credentials():
    result = retrieve(structured())
    audit = result.search_passes[0]
    assert audit.provider is MarketSourceProvider.ADZUNA
    assert audit.request_parameters["title"] == "Senior Java Developer"
    assert audit.request_parameters["location"] == "Toronto, Canada"
    assert audit.request_parameters["page"] == 1
    assert audit.request_parameters["country"] == "ca"
    assert audit.succeeded
    assert not {"app_id", "app_key", "api_key"} & audit.request_parameters.keys()


def test_failed_structured_query_is_distinct_from_zero_result_success():
    from ai_career_navigator.market import MarketTimeoutError

    request = StructuredJobSearchRequest(title="Senior Java Developer", location="Toronto")
    audit = _failed_structured_pass(request, MarketTimeoutError("not retained detail"))
    assert audit.succeeded is False
    assert audit.failure_category == "MarketTimeoutError"
    assert audit.raw_result_count == 0
    assert audit.request_parameters == request.model_dump(mode="json")


@pytest.mark.parametrize(
    "title,target,body,expected",
    [
        ("Sr. Java Developer", "Senior Java Developer", "", "TARGET_VARIANT"),
        (
            "Senior Java Developer — Spring Boot & Cloud",
            "Senior Java Developer",
            "We seek a Senior Java Developer. Skills: Spring Boot and Cloud.",
            "TARGET_VARIANT",
        ),
        (
            "Senior Java Developer — Team Lead",
            "Senior Java Developer",
            "We seek a Senior Java Developer. Team Lead responsibilities.",
            "RELATED_TITLE",
        ),
        (
            "Senior Java Developer — Spring Boot & Cloud",
            "Senior Java Developer",
            "",
            "RELATED_TITLE",
        ),
        ("Sr. Financial Analyst", "Senior Financial Analyst", "", "TARGET_VARIANT"),
        (
            "Senior Financial Analyst — Forecasting & Reporting",
            "Senior Financial Analyst",
            "The Senior Financial Analyst provides forecasting and reporting.",
            "TARGET_VARIANT",
        ),
        ("Junior Java Developer", "Senior Java Developer", "", "RELATED_TITLE"),
    ],
)
def test_role_equivalence_is_generic_and_grounded(title, target, body, expected):
    assert assess_title(title, target, posting_text=body).value == expected


def test_equivalent_suffix_keeps_original_title_and_primary_sample():
    result = retrieve(structured(title="Senior Java Developer — Spring Boot & Cloud"))
    assert result.snapshot.exact_title_count == 0
    assert result.snapshot.target_variant_count == 1
    assert result.postings[0].original_title.endswith("Spring Boot & Cloud")
    assert result.postings[0].title_match_kind == "DESCRIPTIVE_SUFFIX_GROUNDED"


def test_suffix_role_need_not_be_repeated_and_plural_descriptor_is_grounded():
    title = "Sr. Python Developer – APIs"
    body = f"{title}. Qualifications: production Python and API integration experience."
    assert (
        assess_title(title, "Senior Python Developer", posting_text=body).value == "TARGET_VARIANT"
    )
    assert (
        assess_title(title, "Senior Python Developer", posting_text=f"{title}. Apply now.").value
        == "RELATED_TITLE"
    )
    assert (
        assess_title(
            "Sr. Python Developer – Team Lead",
            "Senior Python Developer",
            posting_text="Qualifications: Python, team leadership and API experience.",
        ).value
        == "RELATED_TITLE"
    )


def test_shortened_secondary_title_cannot_supply_missing_suffix_evidence():
    first = retrieve(
        structured(
            title="Sr. Java Developer – Unstated Specialism",
            description="Sr. Java Developer – Unstated Specialism. "
            "Qualifications: production Java experience.",
        )
    )
    # A body lacking the descriptor leaves the original posting outside the primary cohort.
    assert first.snapshot.validated_posting_count == 1
    assert first.snapshot.exact_title_count == first.snapshot.target_variant_count == 0
    assert not first.posting_audits[0].selected_for_primary_evidence
    assert first.posting_audits[0].title_classification == "RELATED_TITLE"
    envelope = retrieve(structured()).posting_evidence[0]
    original = envelope.model_copy(
        update={
            "posting": envelope.posting.model_copy(
                update={"original_title": "Sr. Java Developer – Unstated Specialism"}
            ),
            "primary_content": envelope.primary_content.model_copy(
                update={"title": "Sr. Java Developer – Unstated Specialism"}
            ),
            "title_classification": "RELATED_TITLE",
        }
    )
    shortened = original.model_copy(
        update={
            "primary_source": original.primary_source.model_copy(
                update={"source_id": uuid4(), "source_type": "YOU"}
            ),
            "posting": original.posting.model_copy(
                update={"posting_id": uuid4(), "original_title": "Sr. Java Developer"}
            ),
            "primary_content": original.primary_content.model_copy(
                update={"title": "Sr. Java Developer"}
            ),
            "title_classification": "TARGET_VARIANT",
            "provider_sources": [MarketSourceProvider.YOU],
        }
    )
    merged, count = _merge_duplicate_evidence([original, shortened])
    assert count == 1
    assert merged[0].title_classification == "RELATED_TITLE"
    assert merged[0].posting.original_title.endswith("Unstated Specialism")


def test_related_titles_do_not_fill_primary_when_expansion_not_requested():
    result = retrieve(structured(), structured(2, title="Junior Java Developer"))
    assert result.snapshot.validated_posting_count == 2
    assert result.snapshot.exact_title_count == 1
    assert result.snapshot.related_title_count == 1
    assert not next(
        a for a in result.posting_audits if a.title.startswith("Junior")
    ).selected_for_primary_evidence


def test_related_hits_cannot_stop_primary_pagination():
    client = FakeAdzunaMarketSearchClient(
        [
            StructuredJobSearchPage(
                provider=MarketSourceProvider.ADZUNA,
                page=1,
                results=[structured(index, title="Junior Java Developer") for index in range(10)],
            ),
            StructuredJobSearchPage(
                provider=MarketSourceProvider.ADZUNA, page=2, results=[structured(50)]
            ),
        ]
    )
    result = asyncio.run(
        retrieve_combined_market(
            goal(),
            client,
            now=NOW,
            limits=SearchLimits(
                target_posting_count=1, max_variant_queries=0, discovery_result_count=10
            ),
        )
    )
    assert len(client.requests) == 2
    assert result.snapshot.exact_title_count == 1


def test_shared_query_budget_bounds_both_concurrent_lanes():
    primary = FakeAdzunaMarketSearchClient([])
    you = FakeMarketSearchClient()
    result = asyncio.run(
        retrieve_combined_market(
            goal(),
            primary,
            enrichment_client=you,
            now=NOW,
            limits=SearchLimits(max_total_search_calls=3),
        )
    )
    assert len(primary.requests) + len(you.search_calls) <= 3
    assert len(primary.requests) >= 1 and len(you.search_calls) >= 1
    assert result.effective_budgets["total_search_calls"] == 3


def test_result_rejections_do_not_double_count_candidate_geography_failures():
    url = "https://jobs.ashbyhq.com/employer/remote-role"
    candidate = MarketSearchResult(title="Senior Java Developer", url=url)
    client = FakeMarketSearchClient(
        search_outcomes=[[candidate]],
        content_outcomes={
            url: MarketPageContent(
                url=url,
                title=candidate.title,
                employer="Employer",
                location="India",
                markdown="Senior Java Developer at Employer. Location: India. Requirements: Java.",
            )
        },
    )
    result = asyncio.run(retrieve_current_market(goal(), client, now=NOW, ats_primary=True))
    assert result.you_raw_result_count == 1
    assert result.rejected_result_count == 1
    assert result.rejected_candidate_count == 1
    assert result.posting_audits[0].decision_unit == "POSTING_CANDIDATE"
    assert result.posting_audits[0].parent_result_id


def test_closed_old_and_future_postings_are_excluded_but_unknown_is_explicit():
    result = retrieve(
        structured(1, description="This job is closed."),
        structured(2, created=date(2025, 9, 1)),
        structured(3, created=date(2027, 9, 1)),
        structured(4, created=None),
    )
    assert len(result.postings) == 1
    assert result.postings[0].active_status == "PROVIDER_OBSERVED"
    assert result.postings[0].currentness_basis == "PROVIDER_SEARCH_RESULT"
    assert result.rejected_result_count == 3
    assert sum(a.stage == "CURRENTNESS" for a in result.posting_audits) == 3


def test_older_explicitly_verified_open_posting_policy():
    page = MarketPageContent(
        url="https://employer.example/jobs/1",
        posting_date="2025-01-01",
        active_status="VERIFIED_OPEN",
    )
    assert currentness_rejection(page, as_of=NOW.date(), max_age_days=90) is None


def test_actual_posting_age_changes_ranking():
    result = retrieve(
        structured(1, created=date(2026, 7, 1), requisition_id="OLD"),
        structured(2, created=date(2026, 9, 1), requisition_id="NEW"),
    )
    assert result.postings[0].posting_date == date(2026, 9, 1)
    assert (
        _content_score(result.posting_evidence[0])[-1]
        > _content_score(result.posting_evidence[1])[-1]
    )


def test_distinct_requisitions_override_title_location_and_same_content():
    common = dict(
        source_id=uuid4(),
        original_title="Senior Java Developer",
        employer="Employer",
        location="Toronto",
        extraction_confidence=ConfidenceLevel.HIGH,
        canonical_job_url="https://example.com/jobs/1",
        content_fingerprint="identical",
    )
    first = JobPosting(**common, requisition_id="A")
    second = JobPosting(**common, requisition_id="B")
    assert len(deduplicate_postings([first, second])[0]) == 2
    assert (
        len(deduplicate_postings([first, second.model_copy(update={"requisition_id": "A"})])[0])
        == 1
    )


def test_known_ats_thin_snippet_gets_content_fetch():
    url = "https://jobs.ashbyhq.com/employer/4ad2f901-1234"
    candidate = MarketSearchResult(title="Senior Java Developer", url=url)
    assert is_promising_search_result(candidate, "Senior Java Developer")
    assert not is_promising_search_result(
        candidate.model_copy(update={"url": "https://jobs.ashbyhq.com/employer"}),
        "Senior Java Developer",
    )
    client = FakeMarketSearchClient(
        search_outcomes=[[candidate]],
        content_outcomes={
            url: MarketPageContent(
                url=url,
                title=candidate.title,
                employer="Employer",
                location="Toronto, Canada",
                markdown="Senior Java Developer at Employer in Toronto, Canada. "
                "Responsibilities: design software. Qualifications: Java.",
            )
        },
    )
    result = asyncio.run(retrieve_current_market(goal(), client, now=NOW, ats_primary=True))
    assert client.content_calls == [url]
    assert result.snapshot.validated_posting_count == 1


def test_query_family_does_not_invent_technology_and_supports_discovered_filters(monkeypatch):
    requests = build_you_query_family(build_search_plan(goal()))
    assert len(requests) == 3
    assert all("Spring" not in r.query and "AWS" not in r.query for r in requests)
    assert "Sr." in requests[2].query
    client = YouMcpMarketSearchClient(
        endpoint="https://api.you.com/mcp", api_key="synthetic", timeout_seconds=1
    )
    client._search_properties = {"query", "boost_domains", "include_domains"}
    observed = []

    async def capture(tool, arguments):
        observed.append(arguments)
        return {"results": {"web": []}}

    monkeypatch.setattr(client, "_call", capture)
    asyncio.run(client.search(requests[0]))
    assert observed[0]["include_domains"]
    assert "boost_domains" not in observed[0]
    assert "site:" not in observed[0]["query"]
    client._search_properties = {"query"}
    asyncio.run(client.search(requests[0]))
    assert "boost_domains" not in observed[1]
    assert "site:boards.greenhouse.io" in observed[1]["query"]


def test_structured_job_metadata_preserves_identity_without_fabricating_active_status():
    url = "https://employer.example/jobs/1"
    content = normalize_you_content_payload(
        {
            "url": url,
            "markdown": "Full posting",
            "metadata": {
                "structured_data": {
                    "@type": "JobPosting",
                    "title": "Senior Java Developer",
                    "identifier": {"value": "REQ-1"},
                    "datePosted": "2026-09-01",
                    "hiringOrganization": {"name": "Employer"},
                    "jobLocation": {
                        "address": {"addressLocality": "Toronto", "addressCountry": "Canada"}
                    },
                }
            },
        },
        url,
    )
    assert content.requisition_id == "REQ-1"
    assert content.location == "Toronto, Canada"
    assert content.active_status is None


def test_both_providers_same_vacancy_preserve_structured_fields():
    first = retrieve(structured()).posting_evidence[0]
    other_source = first.primary_source.model_copy(
        update={"source_id": uuid4(), "source_type": "YOU"}
    )
    second = first.model_copy(
        update={
            "primary_source": other_source,
            "posting": first.posting.model_copy(
                update={
                    "posting_id": uuid4(),
                    "source_id": other_source.source_id,
                    "location": "Toronto",
                }
            ),
            "provider_sources": [MarketSourceProvider.YOU],
        }
    )
    merged, duplicate_count = _merge_duplicate_evidence([first, second])
    assert duplicate_count == 1
    assert merged[0].posting.location == "Toronto, Canada"
    assert len(merged[0].provider_sources) == 2
    assert merged[0].field_sources["location"] is MarketSourceProvider.ADZUNA
    assert "location" in merged[0].field_conflicts
