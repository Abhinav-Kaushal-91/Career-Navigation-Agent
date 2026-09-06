import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from ai_career_navigator.domain import (
    ApprovalStatus,
    CareerGoal,
    ConfidenceLevel,
    GeographyScope,
    GoalType,
)
from ai_career_navigator.market import (
    MarketPageContent,
    MarketSearchResult,
    PostingCandidate,
    PostingCandidateAssessment,
    PostingGeographyStatus,
    PostingSourceType,
    PostingTitleMatch,
    SearchLimits,
    SearchPassType,
    retrieve_current_market,
)
from ai_career_navigator.market.mcp.fake_client import FakeMarketSearchClient
from ai_career_navigator.market.requirements import _select_employer_diverse
from ai_career_navigator.market.search_plan import build_you_ats_query

NOW = datetime(2026, 9, 6, tzinfo=UTC)


def _goal() -> CareerGoal:
    return CareerGoal(
        goal_type=GoalType.ROLE_TRANSITION,
        target_role="AI Engineer",
        target_location="Canada",
        geography_scopes=[GeographyScope.COUNTRY],
        approval_status=ApprovalStatus.APPROVED,
        approved_at=NOW,
    )


def _page(url: str, title: str = "AI Engineer", employer: str = "Employer"):
    return MarketPageContent(
        url=url,
        title=title,
        employer=employer,
        location="Canada",
        markdown=(
            f"{title} at {employer}. Location: Canada. "
            "Responsibilities include building production AI systems. "
            "Qualifications include Python and production deployment experience."
        ),
    )


def test_ats_query_is_dynamic_and_excludes_internships() -> None:
    query = build_you_ats_query("AI Engineer", "Canada")

    assert query.startswith('"AI Engineer" Canada')
    assert "site:boards.greenhouse.io" in query
    assert "site:jobs.lever.co" in query
    assert "site:jobs.ashbyhq.com" in query
    assert "site:myworkdayjobs.com" in query
    assert query.endswith("-intern -internship")


def test_ats_query_allows_internships_for_explicit_early_career_targets() -> None:
    query = build_you_ats_query("Junior AI Engineer", "Canada", "Entry level")

    assert "-intern" not in query
    assert "-internship" not in query


def test_you_processes_up_to_ten_results_as_individual_postings() -> None:
    results = [
        MarketSearchResult(
            title="AI Engineer",
            url=f"https://boards.greenhouse.io/employer{i}/jobs/{i}",
        )
        for i in range(11)
    ]
    client = FakeMarketSearchClient(
        search_outcomes=[results],
        content_outcomes={
            item.url: _page(item.url, employer=f"Employer {i}")
            for i, item in enumerate(results)
        },
    )

    result = asyncio.run(
        retrieve_current_market(
            _goal(),
            client,
            limits=SearchLimits(target_posting_count=20, max_content_fetches=20),
            now=NOW,
            ats_primary=True,
        )
    )

    assert result.you_raw_result_count == 11
    assert result.you_direct_posting_count == 10
    assert len(client.content_calls) == 10
    assert result.search_passes[0].pass_type is SearchPassType.ATS_PRIMARY
    assert result.you_fallback_triggered is False


def test_generic_guide_is_context_only_and_cannot_become_posting_evidence() -> None:
    url = "https://example.com/guides/ai-engineer-career-guide"
    client = FakeMarketSearchClient(
        search_outcomes=[[MarketSearchResult(title="AI Engineer", url=url)], []],
        content_outcomes={url: _page(url)},
    )

    result = asyncio.run(
        retrieve_current_market(_goal(), client, now=NOW, ats_primary=True)
    )

    assert result.postings == []
    assert result.you_context_result_count == 1
    assert result.you_fallback_triggered is True
    assert result.posting_audits[0].source_type is PostingSourceType.BACKGROUND_CONTEXT
    assert result.posting_audits[0].selected_for_primary_evidence is False


def test_unspecified_seniority_keeps_staff_posting_as_related_context() -> None:
    url = "https://jobs.lever.co/employer/123"
    client = FakeMarketSearchClient(
        search_outcomes=[[MarketSearchResult(title="Staff AI Engineer", url=url)], []],
        content_outcomes={url: _page(url, title="Staff AI Engineer")},
    )

    result = asyncio.run(
        retrieve_current_market(_goal(), client, now=NOW, ats_primary=True)
    )

    assert len(result.postings) == 1
    assert result.posting_audits[0].title_classification == "RELATED_TITLE"
    assert result.snapshot is not None
    assert result.snapshot.exact_title_count == 0


def test_analysis_cap_prioritizes_distinct_employers() -> None:
    assessments = []
    for index, employer in enumerate(("Employer A", "Employer A", "Employer B")):
        candidate = PostingCandidate(
            source_id=uuid4(),
            source_reference=f"source-{index}",
            source_reference_text=f"AI Engineer at {employer}",
            title="AI Engineer",
            employer=employer,
            location="Canada",
            posting_text="Python production engineering requirements " * 20,
            extraction_confidence=ConfidenceLevel.HIGH,
            provider_sources=["ADZUNA" if index < 2 else "YOU"],
            retrieval_quality="HIGH",
            seniority_classification="STANDARD",
        )
        assessments.append(
            PostingCandidateAssessment(
                candidate=candidate,
                geography_status=PostingGeographyStatus.IN_SCOPE,
                title_match=PostingTitleMatch.EXACT_TARGET,
            )
        )

    selected = _select_employer_diverse(assessments, 2)

    assert {item.candidate.employer for item in selected} == {"Employer A", "Employer B"}


def test_analysis_cap_prioritizes_standard_seniority_before_employer_diversity() -> None:
    assessments = []
    for index, (employer, seniority) in enumerate(
        (("Employer A", "SENIOR"), ("Employer B", "STANDARD"))
    ):
        candidate = PostingCandidate(
            source_id=uuid4(),
            source_reference=f"source-{index}",
            source_reference_text=f"AI Engineer at {employer}",
            title="AI Engineer",
            employer=employer,
            location="Canada",
            posting_text="Python production engineering requirements " * 20,
            extraction_confidence=ConfidenceLevel.HIGH,
            provider_sources=["ADZUNA"],
            retrieval_quality="HIGH",
            seniority_classification=seniority,
        )
        assessments.append(
            PostingCandidateAssessment(
                candidate=candidate,
                geography_status=PostingGeographyStatus.IN_SCOPE,
                title_match=PostingTitleMatch.EXACT_TARGET,
            )
        )

    selected = _select_employer_diverse(assessments, 1)

    assert selected[0].candidate.employer == "Employer B"
