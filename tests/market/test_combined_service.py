import asyncio
from datetime import UTC, datetime

from ai_career_navigator.domain import ApprovalStatus, CareerGoal, GeographyScope, GoalType
from ai_career_navigator.market import (
    FakeAdzunaMarketSearchClient,
    MarketPageContent,
    MarketSearchResult,
    MarketSourceProvider,
    SearchLimits,
    StructuredJobResult,
    StructuredJobSearchPage,
    retrieve_combined_market,
)
from ai_career_navigator.market.errors import MarketTransportError
from ai_career_navigator.market.mcp.fake_client import FakeMarketSearchClient

NOW = datetime(2026, 9, 3, 12, tzinfo=UTC)


def goal() -> CareerGoal:
    return CareerGoal(
        goal_type=GoalType.TARGET_CAREER_PATH,
        target_role="AI Solutions Architect",
        target_location="Canada",
        geography_scopes=[GeographyScope.COUNTRY],
        search_expansion_permission=True,
        approval_status=ApprovalStatus.APPROVED,
        approved_at=NOW,
    )


def job(index: int, *, description: str | None = None) -> StructuredJobResult:
    return StructuredJobResult(
        provider=MarketSourceProvider.ADZUNA,
        provider_job_id=f"adz-{index}",
        title="AI Solutions Architect",
        url=f"https://employer{index}.example/jobs/{index}",
        description=description or ("Production AI architecture and delivery. " * 20),
        company=f"Employer {index}",
        location="Canada",
        created="2026-09-01",
    )


def page(*items: StructuredJobResult) -> StructuredJobSearchPage:
    return StructuredJobSearchPage(
        provider=MarketSourceProvider.ADZUNA,
        page=1,
        total_available=len(items),
        results=list(items),
    )


def run(primary, enrichment=None):  # type: ignore[no-untyped-def]
    return asyncio.run(
        retrieve_combined_market(
            goal(),
            primary,
            enrichment_client=enrichment,
            limits=SearchLimits(
                max_search_queries=1,
                max_variant_queries=0,
                target_posting_count=5,
                discovery_result_count=10,
            ),
            now=NOW,
            max_pages=1,
        )
    )


def test_healthy_adzuna_and_you_discovery_both_run() -> None:
    primary = FakeAdzunaMarketSearchClient([page(job(1), job(2), job(3))])
    you = FakeMarketSearchClient()
    result = run(primary, you)
    assert result.snapshot.validated_posting_count == 3
    assert result.primary_provider is MarketSourceProvider.ADZUNA
    assert result.enrichment_attempt_count == 0
    assert result.parallel_discovery is True
    assert you.search_calls
    assert you.content_calls == []
    assert {source.source_type for source in result.sources} == {"ADZUNA"}


def test_discovery_lanes_start_concurrently() -> None:
    async def execute():  # type: ignore[no-untyped-def]
        primary_started = asyncio.Event()
        you_started = asyncio.Event()

        class CoordinatedPrimary(FakeAdzunaMarketSearchClient):
            async def search_page(self, request):  # type: ignore[no-untyped-def]
                primary_started.set()
                await asyncio.wait_for(you_started.wait(), timeout=0.5)
                return await super().search_page(request)

        class CoordinatedYou(FakeMarketSearchClient):
            async def search(self, request):  # type: ignore[no-untyped-def]
                you_started.set()
                await asyncio.wait_for(primary_started.wait(), timeout=0.5)
                return await super().search(request)

        return await retrieve_combined_market(
            goal(),
            CoordinatedPrimary([page(job(1))]),
            enrichment_client=CoordinatedYou(search_outcomes=[[]]),
            limits=SearchLimits(
                max_search_queries=1,
                max_variant_queries=0,
                target_posting_count=5,
                discovery_result_count=10,
            ),
            now=NOW,
            max_pages=1,
        )

    result = asyncio.run(execute())

    assert result.parallel_discovery is True


def test_parallel_you_posting_is_validated_and_merged() -> None:
    url = "https://jobs.lever.co/synthetic-you-employer/ai-solutions-architect"
    you = FakeMarketSearchClient(
        search_outcomes=[
            [
                MarketSearchResult(
                    title="AI Solutions Architect",
                    url=url,
                    snippets=["AI Solutions Architect in Canada"],
                )
            ]
        ],
        content_outcomes={
            url: MarketPageContent(
                url=url,
                title="AI Solutions Architect",
                employer="You Employer",
                location="Canada",
                markdown=(
                    "AI Solutions Architect — You Employer — Canada. "
                    "Production AI architecture and delivery requirements."
                ),
            )
        },
    )

    result = run(FakeAdzunaMarketSearchClient([page(job(1))]), you)

    assert result.snapshot.validated_posting_count == 2
    assert result.adzuna_validated_count == 1
    assert result.you_validated_count == 1
    assert {source.source_type for source in result.sources} == {"ADZUNA", "YOU"}
    assert result.source_coverage_confidence.value == "MODERATE"


def test_cross_source_duplicate_does_not_inflate_posting_count() -> None:
    primary_job = job(1).model_copy(
        update={"url": "https://jobs.lever.co/synthetic-employer/ai-solutions-architect"}
    )
    you = FakeMarketSearchClient(
        search_outcomes=[
            [
                MarketSearchResult(
                    title=primary_job.title,
                    url=primary_job.url,
                    snippets=["AI Solutions Architect in Canada"],
                )
            ]
        ],
        content_outcomes={
            primary_job.url: MarketPageContent(
                url=primary_job.url,
                title=primary_job.title,
                employer=primary_job.company,
                location=primary_job.location,
                markdown=(
                    "AI Solutions Architect — Employer 1 — Canada. "
                    "Responsibilities: design production AI solutions with documented architecture "
                    "decisions, deploy the services, and monitor their reliability. Work with "
                    "business stakeholders to translate use cases into maintainable designs. "
                    "Qualifications: demonstrated delivery of production AI applications; "
                    "experience with Python, cloud services, automated tests, and API integration. "
                    "Candidates "
                    "must explain security and operational trade-offs in prior solutions. "
                    "Preferred: mentoring engineers and reviewing architecture proposals. "
                    "Apply through this employer's current Canadian vacancy page."
                ),
                content_complete=True,
            )
        },
    )

    result = run(FakeAdzunaMarketSearchClient([page(primary_job)]), you)

    assert result.snapshot.validated_posting_count == 1
    assert result.snapshot.distinct_employer_count == 1
    assert result.cross_source_match_count == 1
    assert result.sources[0].source_type == "ADZUNA"
    assert result.posting_evidence[0].selected_content_source is MarketSourceProvider.YOU
    assert result.posting_evidence[0].provider_sources == [
        MarketSourceProvider.ADZUNA,
        MarketSourceProvider.YOU,
    ]
    assert len(result.posting_evidence[0].supporting_sources) == 1


def test_thin_ats_duplicate_does_not_replace_substantive_structured_body() -> None:
    primary_job = job(1).model_copy(
        update={"url": "https://jobs.lever.co/synthetic-employer/ai-solutions-architect"}
    )
    you = FakeMarketSearchClient(
        search_outcomes=[[MarketSearchResult(title=primary_job.title, url=primary_job.url)]],
        content_outcomes={
            primary_job.url: MarketPageContent(
                url=primary_job.url,
                title=primary_job.title,
                employer=primary_job.company,
                location=primary_job.location,
                markdown="AI Solutions Architect — Employer 1 — Canada. Qualifications: Python.",
                content_complete=False,
            )
        },
    )

    result = run(FakeAdzunaMarketSearchClient([page(primary_job)]), you)

    assert result.snapshot.validated_posting_count == 1
    assert result.cross_source_match_count == 1
    retained = result.posting_evidence[0]
    assert retained.primary_content.markdown == primary_job.description
    assert retained.selected_content_source is MarketSourceProvider.ADZUNA
    assert set(retained.provider_sources) == {MarketSourceProvider.ADZUNA, MarketSourceProvider.YOU}


def test_thin_posting_is_enriched_without_overwriting_structured_fields() -> None:
    primary_job = job(1, description="Short description")
    primary = FakeAdzunaMarketSearchClient([page(primary_job)])
    you = FakeMarketSearchClient(
        content_outcomes={
            primary_job.url: MarketPageContent(
                url=primary_job.url,
                title=primary_job.title,
                employer=primary_job.company,
                location="Toronto, Ontario",
                markdown="Supporting responsibilities and qualifications.",
            )
        }
    )
    result = run(primary, you)
    evidence = result.posting_evidence[0]
    assert result.enrichment_attempt_count == 1
    assert result.enrichment_success_count == 1
    assert evidence.posting.location == "Canada"
    assert evidence.primary_source.source_type == "ADZUNA"
    assert evidence.supporting_sources[0].source_type == "YOU"
    assert evidence.primary_content.markdown == "Supporting responsibilities and qualifications."
    assert any(item.markdown == "Short description" for item in evidence.supporting_contents)
    assert evidence.selected_content_source is MarketSourceProvider.YOU


def test_description_at_thin_threshold_is_enrichment_eligible() -> None:
    primary_job = job(1, description="x" * 500)
    you = FakeMarketSearchClient(
        content_outcomes={
            primary_job.url: MarketPageContent(
                url=primary_job.url,
                title=primary_job.title,
                employer=primary_job.company,
                location=primary_job.location,
                markdown="Supporting qualifications and responsibilities. " * 20,
            )
        }
    )

    result = run(FakeAdzunaMarketSearchClient([page(primary_job)]), you)

    assert result.enrichment_attempt_count == 1
    assert result.enrichment_success_count == 1


def test_conflicting_enrichment_is_rejected() -> None:
    primary_job = job(1, description="Short")
    primary = FakeAdzunaMarketSearchClient([page(primary_job)])
    you = FakeMarketSearchClient(
        content_outcomes={
            primary_job.url: MarketPageContent(
                url=primary_job.url,
                title="Data Entry Clerk",
                employer="Different Employer",
                location="United States",
                markdown="Unrelated posting.",
            )
        }
    )
    result = run(primary, you)
    evidence = result.posting_evidence[0]
    assert result.enrichment_success_count == 0
    assert evidence.supporting_sources == []
    assert any("conflicted" in limitation for limitation in evidence.limitations)


def test_generic_page_title_is_accepted_only_when_posting_identity_is_grounded() -> None:
    primary_job = job(1, description="Short")
    you = FakeMarketSearchClient(
        content_outcomes={
            primary_job.url: MarketPageContent(
                url=primary_job.url,
                title="Employer Careers",
                markdown=(
                    "AI Solutions Architect at Employer 1. Required experience with "
                    "production AI architecture and delivery in Canada."
                ),
            )
        }
    )

    result = run(FakeAdzunaMarketSearchClient([page(primary_job)]), you)

    assert result.enrichment_success_count == 1
    assert "Required experience" in result.posting_evidence[0].primary_content.markdown


def test_generic_page_title_without_grounded_posting_identity_is_rejected() -> None:
    primary_job = job(1, description="Short")
    you = FakeMarketSearchClient(
        content_outcomes={
            primary_job.url: MarketPageContent(
                url=primary_job.url,
                title="Employer Careers",
                markdown="Browse all current vacancies and learn about our culture.",
            )
        }
    )

    result = run(FakeAdzunaMarketSearchClient([page(primary_job)]), you)

    assert result.enrichment_success_count == 0


def test_location_conflict_does_not_overwrite_adzuna_location() -> None:
    primary_job = job(1, description="Short").model_copy(update={"location": "Toronto, Ontario"})
    you = FakeMarketSearchClient(
        content_outcomes={
            primary_job.url: MarketPageContent(
                url=primary_job.url,
                title=primary_job.title,
                employer=primary_job.company,
                location="Vancouver, British Columbia",
                markdown="Conflicting location evidence.",
            )
        }
    )
    result = run(FakeAdzunaMarketSearchClient([page(primary_job)]), you)
    evidence = result.posting_evidence[0]
    assert evidence.posting.location == "Toronto, Ontario"
    assert evidence.supporting_sources == []
    assert any("conflicted" in limitation for limitation in evidence.limitations)


def test_enrichment_failure_preserves_primary_posting() -> None:
    primary_job = job(1, description="Short")
    result = run(
        FakeAdzunaMarketSearchClient([page(primary_job)]),
        FakeMarketSearchClient(
            content_outcomes={primary_job.url: MarketTransportError("support unavailable")}
        ),
    )
    assert result.snapshot.validated_posting_count == 1
    assert result.posting_evidence[0].primary_source.source_type == "ADZUNA"
    assert result.posting_evidence[0].supporting_sources == []
    assert any("unavailable" in limitation for limitation in result.posting_evidence[0].limitations)


def test_cross_source_duplicates_do_not_inflate_market_signals() -> None:
    first = job(1)
    duplicate = first.model_copy(
        update={"provider_job_id": "adz-duplicate", "url": "https://other.example/job/1"}
    )
    result = run(FakeAdzunaMarketSearchClient([page(first, duplicate)]))
    assert result.snapshot.validated_posting_count == 1
    assert result.snapshot.duplicate_posting_count == 1


def test_adzuna_failure_preserves_parallel_you_lane_in_degraded_mode() -> None:
    primary = FakeAdzunaMarketSearchClient([MarketTransportError("offline")])
    result = run(primary, FakeMarketSearchClient(search_outcomes=[[]]))
    assert result.degraded_discovery is True
    assert result.source_coverage_confidence.value == "INSUFFICIENT"
    assert any("Adzuna parallel discovery" in item for item in result.snapshot.limitations)


def test_related_expansion_runs_after_exact_pass_and_stays_separate() -> None:
    observed = job(1).model_copy(update={"title": "AI Platform Architect"})
    expanded = job(2).model_copy(update={"title": "AI Platform Architect"})
    primary = FakeAdzunaMarketSearchClient([page(observed), page(expanded)])
    result = run(primary)
    assert [request.pass_type.value for request in primary.requests] == [
        "DIRECT_SOURCE",
        "RELATED_TITLE",
    ]
    assert result.exact_title_validated_count == 0
    assert result.target_variant_validated_count == 0
    assert result.related_title_validated_count == 2
