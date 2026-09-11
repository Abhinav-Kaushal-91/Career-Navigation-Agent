from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from ai_career_navigator.career import assess_bridge_roles, assess_timeline
from ai_career_navigator.career.path_schemas import (
    BridgeAnalysisResult,
    BridgeAnalysisStatus,
    TimelineAnalysisStatus,
)
from ai_career_navigator.domain import (
    ApprovalStatus,
    BridgeOutcome,
    CandidateAccessibility,
    CandidateProfile,
    CareerGoal,
    CareerStage,
    ComparisonScope,
    ConfidenceLevel,
    CurrentMarketSnapshot,
    EmployerDiversity,
    EvidenceConfirmationStatus,
    EvidenceItem,
    EvidenceMaturity,
    GapCategory,
    GapItem,
    GapSeverity,
    GoalType,
    JobPosting,
    MarketConcentration,
    OpportunityAvailability,
    RequirementCategory,
    RequirementFrequency,
    RoleAssessment,
    RoleRequirement,
    TimelineClassification,
)
from ai_career_navigator.market import (
    MarketRequirementAnalysis,
    MarketRequirementSummary,
    RequirementRunStatus,
)

NOW = datetime(2026, 9, 4, tzinfo=UTC)


def profile() -> CandidateProfile:
    item = EvidenceItem(
        evidence_type="skill",
        source_type="manual",
        source_reference="profile",
        capability="REST APIs",
        description="Production API integration.",
        maturity_level=EvidenceMaturity.PRODUCTION,
        confirmation_status=EvidenceConfirmationStatus.EXPLICIT,
        confidence=ConfidenceLevel.HIGH,
        approved_by_user=True,
    )
    return CandidateProfile(
        career_stage=CareerStage.SENIOR_INDIVIDUAL_CONTRIBUTOR,
        evidence_items=[item],
        approval_status=ApprovalStatus.APPROVED,
        confirmed_at=NOW,
    )


def goal(*, months=24, willingness=True, exclusions=None) -> CareerGoal:
    return CareerGoal(
        goal_type=GoalType.TARGET_CAREER_PATH,
        target_role="AI Solutions Architect",
        target_timeline_months=months,
        target_location="Toronto",
        bridge_role_willingness=willingness,
        exclusions=exclusions or [],
        approval_status=ApprovalStatus.APPROVED,
        approved_at=NOW,
    )


def gap(
    target: str,
    *,
    category: GapCategory = GapCategory.EXPERIENCE,
    severity: GapSeverity = GapSeverity.HIGH,
    hard: bool = False,
) -> GapItem:
    requirement_id = uuid4()
    return GapItem(
        requirement_id=requirement_id,
        requirement_ids=[requirement_id],
        comparison_scope=ComparisonScope.EXACT_TARGET,
        requirement_frequency=RequirementFrequency.COMMON,
        category=category,
        target_expectation=target,
        remaining_difference=f"Confirmed {target} evidence is missing.",
        severity=severity,
        hard_blocker=hard,
        evidence_needed=f"Confirmed {target} outcome",
        confidence=ConfidenceLevel.HIGH,
    )


def role(accessibility: CandidateAccessibility, gaps: list[GapItem]) -> RoleAssessment:
    return RoleAssessment(
        target_role="AI Solutions Architect",
        gaps=gaps,
        candidate_accessibility=accessibility,
        explanation="Evidence-grounded assessment.",
        confidence=ConfidenceLevel.HIGH,
    )


def market(role_capabilities: dict[str, list[str]]) -> MarketRequirementAnalysis:
    postings = []
    requirements = []
    for title, capabilities in role_capabilities.items():
        posting_id = uuid4()
        postings.append(
            JobPosting(
                posting_id=posting_id,
                source_id=uuid4(),
                original_title=title,
                normalized_title=title,
                extraction_confidence=ConfidenceLevel.HIGH,
            )
        )
        for capability in capabilities:
            requirements.append(
                RoleRequirement(
                    posting_id=posting_id,
                    category=RequirementCategory.TECHNICAL,
                    requirement_text=capability,
                    normalized_capability=capability,
                    extraction_confidence=ConfidenceLevel.HIGH,
                )
            )
    summary = MarketRequirementSummary(
        target_role="AI Solutions Architect",
        geography="Toronto",
        source_page_count=len(postings),
        identified_candidate_count=len(postings),
        validated_in_scope_posting_count=len(postings),
        analyzed_posting_count=len(postings),
        exact_title_analyzed_count=0,
        related_title_analyzed_count=len(postings),
        out_of_scope_count=0,
        unclear_geography_count=0,
        irrelevant_title_count=0,
    )
    return MarketRequirementAnalysis(
        status=RequirementRunStatus.SUCCEEDED,
        postings=postings,
        requirements=requirements,
        summary=summary,
    )


def snapshot(titles: list[str]) -> CurrentMarketSnapshot:
    return CurrentMarketSnapshot(
        target_role="AI Solutions Architect",
        geography="Toronto",
        search_date=date(2026, 9, 4),
        exact_title_count=0,
        related_title_count=len(titles),
        validated_posting_count=len(titles),
        distinct_employer_count=0,
        related_titles=titles,
        opportunity_availability=OpportunityAvailability.MODERATE,
        employer_diversity=EmployerDiversity.INSUFFICIENT_EVIDENCE,
        market_concentration=MarketConcentration.INSUFFICIENT_EVIDENCE,
        evidence_confidence=ConfidenceLevel.HIGH,
    )


def bridge_result(outcome: BridgeOutcome, *, helpful=False) -> BridgeAnalysisResult:
    return BridgeAnalysisResult(
        status=BridgeAnalysisStatus.SUCCEEDED,
        outcome=outcome,
        bridge_would_help=helpful,
    )


def test_apply_now_does_not_require_bridge() -> None:
    result = assess_bridge_roles(
        profile(), goal(), role(CandidateAccessibility.APPLY_NOW, []), market({}), []
    )
    assert result.outcome is BridgeOutcome.NO_BRIDGE_REQUIRED
    assert result.assessments[0].bridge_role is None


def test_observed_bridge_reduces_specific_material_gap_ids() -> None:
    production = gap("Production AI")
    observed = {"AI Automation Engineer": ["REST APIs", "Production AI"]}
    result = assess_bridge_roles(
        profile(),
        goal(),
        role(CandidateAccessibility.ASPIRATIONAL, [production]),
        market(observed),
        list(observed),
    )
    assert result.outcome is BridgeOutcome.RECOMMENDED_BRIDGE
    assert result.assessments[0].bridge_role == "AI Automation Engineer"
    assert result.assessments[0].gaps_reduced == [str(production.gap_id)]
    assert result.assessments[0].target_capabilities_gained == ["Production AI"]
    assert result.assessments[0].evidence_building_value == "HIGH"


def test_multiple_observed_bridges_are_bounded_and_gap_grounded() -> None:
    gaps = [gap("Production AI"), gap("Cloud AI"), gap("Architecture Ownership")]
    observed = {
        "AI Automation Engineer": ["Production AI"],
        "Cloud AI Engineer": ["Cloud AI"],
        "AI Platform Engineer": ["Architecture Ownership"],
        "Unhelpful Analyst": ["Spreadsheets"],
    }
    result = assess_bridge_roles(
        profile(),
        goal(willingness=None),
        role(CandidateAccessibility.ASPIRATIONAL, gaps),
        market(observed),
        list(observed),
    )
    assert result.outcome is BridgeOutcome.MULTIPLE_PLAUSIBLE_BRIDGES
    assert len(result.assessments) == 3
    known_ids = {str(item.gap_id) for item in gaps}
    assert all(set(item.gaps_reduced) <= known_ids for item in result.assessments)


def test_unobserved_or_non_gap_reducing_titles_are_not_recommended() -> None:
    result = assess_bridge_roles(
        profile(),
        goal(),
        role(CandidateAccessibility.ASPIRATIONAL, [gap("Production AI")]),
        market({"Observed Analyst": ["Spreadsheets"]}),
        ["Observed Analyst", "Invented AI Engineer"],
    )
    assert result.outcome is BridgeOutcome.NO_VALID_BRIDGE_ROLE
    assert result.assessments[0].bridge_role is None


def test_observed_role_above_target_seniority_is_not_a_bridge() -> None:
    production = gap("Production AI")
    observed = {"Senior Director of AI Architecture": ["Production AI"]}

    result = assess_bridge_roles(
        profile(),
        goal(),
        role(CandidateAccessibility.ASPIRATIONAL, [production]),
        market(observed),
        list(observed),
    )

    assert result.outcome is BridgeOutcome.NO_VALID_BRIDGE_ROLE
    assert result.assessments[0].bridge_role is None


def test_explicitly_excluded_observed_title_is_not_recommended() -> None:
    constrained_goal = goal(exclusions=["AI Automation Engineer"])
    result = assess_bridge_roles(
        profile(),
        constrained_goal,
        role(CandidateAccessibility.ASPIRATIONAL, [gap("Production AI")]),
        market({"AI Automation Engineer": ["Production AI"]}),
        ["AI Automation Engineer"],
    )
    assert result.outcome is BridgeOutcome.NO_VALID_BRIDGE_ROLE


def test_hard_blocker_and_user_refusal_prevent_primary_bridge() -> None:
    blocking = gap(
        "CPA",
        category=GapCategory.CREDENTIAL_PREREQUISITE,
        severity=GapSeverity.BLOCKING,
        hard=True,
    )
    observed = {"AI Automation Engineer": ["CPA"]}
    hard_result = assess_bridge_roles(
        profile(),
        goal(),
        role(CandidateAccessibility.POOR_FIT, [blocking]),
        market(observed),
        list(observed),
    )
    refused = assess_bridge_roles(
        profile(),
        goal(willingness=False),
        role(CandidateAccessibility.ASPIRATIONAL, [gap("Production AI")]),
        market({"AI Engineer": ["Production AI"]}),
        ["AI Engineer"],
    )
    assert hard_result.outcome is BridgeOutcome.NO_VALID_BRIDGE_ROLE
    assert hard_result.assessments[0].blockers == [str(blocking.gap_id)]
    assert refused.assessments[0].bridge_role is None
    assert refused.bridge_would_help


@pytest.mark.parametrize(
    ("accessibility", "months", "bridge", "expected"),
    [
        (
            CandidateAccessibility.APPLY_NOW,
            12,
            bridge_result(BridgeOutcome.NO_BRIDGE_REQUIRED),
            TimelineClassification.REALISTIC,
        ),
        (
            CandidateAccessibility.NEAR_TERM_TARGET,
            18,
            bridge_result(BridgeOutcome.RECOMMENDED_BRIDGE, helpful=True),
            TimelineClassification.REALISTIC,
        ),
        (
            CandidateAccessibility.ASPIRATIONAL,
            24,
            bridge_result(BridgeOutcome.RECOMMENDED_BRIDGE, helpful=True),
            TimelineClassification.AGGRESSIVE_BUT_PLAUSIBLE,
        ),
        (
            CandidateAccessibility.ASPIRATIONAL,
            6,
            bridge_result(BridgeOutcome.RECOMMENDED_BRIDGE, helpful=True),
            TimelineClassification.UNLIKELY_WITHOUT_INTERMEDIATE_ROLE,
        ),
        (
            CandidateAccessibility.INSUFFICIENT_CANDIDATE_EVIDENCE,
            24,
            bridge_result(BridgeOutcome.INSUFFICIENT_EVIDENCE),
            TimelineClassification.UNSUPPORTED_INSUFFICIENT_EVIDENCE,
        ),
    ],
)
def test_timeline_scenarios(accessibility, months, bridge, expected) -> None:
    result = assess_timeline(
        goal(months=months), role(accessibility, [gap("Production AI")]), bridge, snapshot([])
    )
    assert result.assessment.classification is expected


@pytest.mark.parametrize(
    "accessibility",
    [
        CandidateAccessibility.NEAR_TERM_TARGET,
        CandidateAccessibility.INSUFFICIENT_CANDIDATE_EVIDENCE,
    ],
)
def test_approved_no_fixed_timeline_is_supported_without_fake_precision(accessibility) -> None:
    result = assess_timeline(
        goal(months=None),
        role(accessibility, [gap("Production AI")]),
        bridge_result(BridgeOutcome.RECOMMENDED_BRIDGE, helpful=True),
        snapshot([]),
    )
    assert result.assessment.requested_months is None
    assert result.assessment.classification is TimelineClassification.NO_FIXED_TIMELINE
    assert result.status is TimelineAnalysisStatus.SUCCEEDED
    assert result.assessment.confidence is not ConfidenceLevel.INSUFFICIENT
    serialized = result.model_dump_json()
    assert "%" not in serialized


def test_unconfirmed_missing_timeline_remains_incomplete() -> None:
    incomplete = goal(months=None).model_copy(
        update={"approval_status": ApprovalStatus.DRAFT, "approved_at": None}
    )
    result = assess_timeline(
        incomplete,
        role(CandidateAccessibility.NEAR_TERM_TARGET, [gap("Production AI")]),
        bridge_result(BridgeOutcome.RECOMMENDED_BRIDGE, helpful=True),
        snapshot([]),
    )

    assert (
        result.assessment.classification is TimelineClassification.UNSUPPORTED_INSUFFICIENT_EVIDENCE
    )
    assert result.status is TimelineAnalysisStatus.INSUFFICIENT


def test_refused_helpful_bridge_makes_timeline_unlikely() -> None:
    target_gap = gap("Production AI")
    refused_goal = goal(months=24, willingness=False)
    refused_bridge = assess_bridge_roles(
        profile(),
        refused_goal,
        role(CandidateAccessibility.ASPIRATIONAL, [target_gap]),
        market({"AI Automation Engineer": ["Production AI"]}),
        ["AI Automation Engineer"],
    )
    result = assess_timeline(
        refused_goal,
        role(CandidateAccessibility.ASPIRATIONAL, [target_gap]),
        refused_bridge,
        snapshot(["AI Automation Engineer"]),
    )
    assert (
        result.assessment.classification
        is TimelineClassification.UNLIKELY_WITHOUT_INTERMEDIATE_ROLE
    )


def test_hard_blocker_without_duration_evidence_is_unsupported() -> None:
    blocking = gap(
        "CPA",
        category=GapCategory.CREDENTIAL_PREREQUISITE,
        severity=GapSeverity.BLOCKING,
        hard=True,
    )
    result = assess_timeline(
        goal(months=24),
        role(CandidateAccessibility.POOR_FIT, [blocking]),
        bridge_result(BridgeOutcome.NO_VALID_BRIDGE_ROLE),
        snapshot([]),
    )
    assert (
        result.assessment.classification is TimelineClassification.UNSUPPORTED_INSUFFICIENT_EVIDENCE
    )
