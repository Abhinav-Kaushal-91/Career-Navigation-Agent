from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from ai_career_navigator.career import assess_candidate_accessibility
from ai_career_navigator.domain import (
    ApprovalStatus,
    CandidateAccessibility,
    CandidateProfile,
    CareerGoal,
    CareerStage,
    ComparisonScope,
    ConfidenceLevel,
    CurrentMarketSnapshot,
    EmployerDiversity,
    GapCategory,
    GapSeverity,
    GoalType,
    MarketConcentration,
    MatchType,
    OpportunityAvailability,
    ProductionContextDifference,
    RequirementCategory,
    RequirementComparison,
    RoleRequirement,
)
from ai_career_navigator.market import (
    AggregatedRequirement,
    MarketRequirementAnalysis,
    MarketRequirementSummary,
    RequirementRunStatus,
)

NOW = datetime(2026, 9, 4, tzinfo=UTC)


def inputs(
    categories: list[RequirementCategory],
    matches: list[MatchType],
    *,
    capability: str = "Python",
    mandatory: bool = True,
    preferred: bool = False,
    frequency: float = 0.75,
    scope: ComparisonScope = ComparisonScope.EXACT_TARGET,
    differences: list[str] | None = None,
):
    requirements = []
    comparisons = []
    for index, (category, match) in enumerate(zip(categories, matches, strict=True)):
        posting_id = uuid4()
        req = RoleRequirement(
            posting_id=posting_id,
            category=category,
            requirement_text=f"{capability} required",
            normalized_capability=capability,
            mandatory=mandatory,
            preferred=preferred,
            frequency_within_sample=frequency,
            extraction_confidence=ConfidenceLevel.HIGH,
        )
        requirements.append(req)
        comparisons.append(
            RequirementComparison(
                requirement_id=req.requirement_id,
                posting_id=posting_id,
                comparison_scope=scope,
                match_type=match,
                production_context_difference=(
                    ProductionContextDifference.LIMITED_PRODUCTION_DEPTH
                    if match is MatchType.TRANSFERABLE_MATCH
                    else ProductionContextDifference.NONE
                ),
                remaining_difference=(differences or [f"No confirmed {capability} evidence."])[
                    min(index, len(differences or [""]) - 1)
                ],
                confidence=ConfidenceLevel.HIGH,
            )
        )
    aggregate = AggregatedRequirement(
        category=categories[0],
        normalized_capability=capability,
        requirement_ids=[item.requirement_id for item in requirements],
        exact_title_occurrence_count=len(requirements)
        if scope is ComparisonScope.EXACT_TARGET
        else 0,
        related_title_occurrence_count=len(requirements)
        if scope is ComparisonScope.COMBINED_RELATED
        else 0,
        exact_title_frequency=frequency if scope is ComparisonScope.EXACT_TARGET else None,
        combined_frequency=frequency,
    )
    exact = len(requirements) if scope is ComparisonScope.EXACT_TARGET else 0
    related = len(requirements) - exact
    summary = MarketRequirementSummary(
        target_role="AI Architect",
        geography="Toronto",
        source_page_count=len(requirements),
        identified_candidate_count=len(requirements),
        validated_in_scope_posting_count=len(requirements),
        analyzed_posting_count=len(requirements),
        exact_title_analyzed_count=exact,
        related_title_analyzed_count=related,
        out_of_scope_count=0,
        unclear_geography_count=0,
        irrelevant_title_count=0,
        requirements=[aggregate],
    )
    market = MarketRequirementAnalysis(
        status=RequirementRunStatus.SUCCEEDED,
        requirements=requirements,
        summary=summary,
    )
    snapshot = CurrentMarketSnapshot(
        target_role="AI Architect",
        geography="Toronto",
        search_date=date(2026, 9, 4),
        exact_title_count=exact,
        related_title_count=related,
        validated_posting_count=len(requirements),
        distinct_employer_count=0,
        opportunity_availability=OpportunityAvailability.STRONG,
        employer_diversity=EmployerDiversity.INSUFFICIENT_EVIDENCE,
        market_concentration=MarketConcentration.INSUFFICIENT_EVIDENCE,
        evidence_confidence=ConfidenceLevel.HIGH,
    )
    profile = CandidateProfile(
        career_stage=CareerStage.MID_CAREER,
        approval_status=ApprovalStatus.APPROVED,
        confirmed_at=NOW,
    )
    goal = CareerGoal(
        goal_type=GoalType.TARGET_CAREER_PATH,
        target_role="AI Architect",
        approval_status=ApprovalStatus.APPROVED,
        approved_at=NOW,
    )
    return profile, goal, snapshot, market, comparisons


@pytest.mark.parametrize(
    ("category", "match", "difference", "expected"),
    [
        (
            RequirementCategory.TECHNICAL,
            MatchType.NO_CONFIRMED_MATCH,
            "Missing skill.",
            GapCategory.SKILL,
        ),
        (
            RequirementCategory.EXPERIENCE,
            MatchType.PARTIAL_MATCH,
            "3 years vs 5 years.",
            GapCategory.EXPERIENCE,
        ),
        (
            RequirementCategory.LEADERSHIP,
            MatchType.PARTIAL_MATCH,
            "Architecture ownership not confirmed.",
            GapCategory.LEADERSHIP_SCOPE,
        ),
        (
            RequirementCategory.TECHNICAL,
            MatchType.TRANSFERABLE_MATCH,
            "Direct proof not confirmed.",
            GapCategory.EVIDENCE,
        ),
        (
            RequirementCategory.CREDENTIAL,
            MatchType.NO_CONFIRMED_MATCH,
            "Certification absent.",
            GapCategory.CREDENTIAL_PREREQUISITE,
        ),
    ],
)
def test_gap_categories(category, match, difference, expected) -> None:
    args = inputs([category], [match], differences=[difference])
    result = assess_candidate_accessibility(*args)
    assert result.role_assessment.gaps[0].category is expected


def test_transferable_match_without_concrete_residual_creates_no_material_gap() -> None:
    profile, goal, snapshot, market, comparisons = inputs(
        [RequirementCategory.TECHNICAL], [MatchType.TRANSFERABLE_MATCH]
    )
    comparisons = [
        comparisons[0].model_copy(
            update={
                "remaining_difference": None,
                "production_context_difference": ProductionContextDifference.NONE,
            }
        )
    ]

    result = assess_candidate_accessibility(profile, goal, snapshot, market, comparisons)

    assert result.role_assessment.gaps == []


def test_duplicate_posting_gaps_consolidate_and_preserve_all_requirement_ids() -> None:
    args = inputs([RequirementCategory.TECHNICAL] * 8, [MatchType.NO_CONFIRMED_MATCH] * 8)
    result = assess_candidate_accessibility(*args)
    assert len(result.role_assessment.gaps) == 1
    assert len(result.role_assessment.gaps[0].requirement_ids) == 8


def test_missing_mandatory_license_is_blocking() -> None:
    args = inputs(
        [RequirementCategory.CREDENTIAL], [MatchType.NO_CONFIRMED_MATCH], capability="CPA"
    )
    gap = assess_candidate_accessibility(*args).role_assessment.gaps[0]
    assert gap.hard_blocker
    assert gap.severity is GapSeverity.BLOCKING


def test_related_only_requirement_cannot_become_high_severity() -> None:
    args = inputs(
        [RequirementCategory.TECHNICAL],
        [MatchType.NO_CONFIRMED_MATCH],
        scope=ComparisonScope.COMBINED_RELATED,
    )
    gap = assess_candidate_accessibility(*args).role_assessment.gaps[0]
    assert gap.comparison_scope is ComparisonScope.RELATED_TITLE
    assert gap.severity is GapSeverity.MODERATE


def test_market_availability_does_not_change_accessibility() -> None:
    args = list(inputs([RequirementCategory.TECHNICAL], [MatchType.DIRECT_MATCH]))
    strong = assess_candidate_accessibility(*args).role_assessment.candidate_accessibility
    args[2] = args[2].model_copy(
        update={"opportunity_availability": OpportunityAvailability.SPARSE}
    )
    sparse = assess_candidate_accessibility(*args).role_assessment.candidate_accessibility
    assert strong is sparse is CandidateAccessibility.APPLY_NOW
