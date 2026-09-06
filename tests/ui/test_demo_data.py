from ai_career_navigator.domain import (
    CandidateAccessibility,
    EmployerDiversity,
    GapCategory,
    OpportunityAvailability,
)
from ai_career_navigator.ui import demo_data


def test_demo_data_uses_valid_v1_models() -> None:
    assert demo_data.CANDIDATE_PROFILE.current_role == "Senior UiPath Developer"
    assert demo_data.CAREER_GOAL.target_role == "AI Solutions Architect"
    assert demo_data.MARKET_SNAPSHOT.opportunity_availability is OpportunityAvailability.STRONG
    assert demo_data.MARKET_SNAPSHOT.employer_diversity is EmployerDiversity.HIGH
    assert demo_data.ROLE_ASSESSMENT.candidate_accessibility is CandidateAccessibility.ASPIRATIONAL
    assert demo_data.CAREER_PLAN.timeline_assessment == demo_data.TIMELINE_ASSESSMENT


def test_demo_gap_data_preserves_five_category_presentation() -> None:
    actual_categories = {gap.category for gap in demo_data.GAPS}

    assert actual_categories == {
        GapCategory.SKILL,
        GapCategory.EXPERIENCE,
        GapCategory.LEADERSHIP_SCOPE,
        GapCategory.EVIDENCE,
    }
    assert GapCategory.CREDENTIAL_PREREQUISITE not in actual_categories


def test_demo_models_round_trip_through_json() -> None:
    plan_type = type(demo_data.CAREER_PLAN)
    restored = plan_type.model_validate_json(demo_data.CAREER_PLAN.model_dump_json())

    assert restored == demo_data.CAREER_PLAN
