from datetime import UTC, datetime

import pytest

from ai_career_navigator.domain import ApprovalStatus, CareerGoal, GeographyScope, GoalType
from ai_career_navigator.market import (
    MarketConfigurationError,
    SearchPlanStatus,
    build_search_plan,
)


def goal(**overrides: object) -> CareerGoal:
    values: dict[str, object] = {
        "goal_type": GoalType.TARGET_CAREER_PATH,
        "target_role": "AI Solutions Architect",
        "target_location": "Toronto, Canada",
        "approval_status": ApprovalStatus.APPROVED,
        "approved_at": datetime(2026, 9, 3, tzinfo=UTC),
    }
    values.update(overrides)
    return CareerGoal(**values)


def test_exact_title_query_is_deterministic_and_geography_scoped() -> None:
    plan = build_search_plan(goal())

    assert plan.direct_source_queries == [
        '"AI Solutions Architect" "Toronto, ON" careers',
        '"AI Solutions Architect" Toronto Ontario careers',
    ]
    assert plan.exact_queries == [
        '"AI Solutions Architect" jobs "Toronto, ON"',
        '"AI Solutions Architect" jobs Toronto Ontario',
    ]
    assert plan.allowed_geography_scopes == [GeographyScope.STRICT_CITY]
    assert plan.status is SearchPlanStatus.READY


def test_explicit_seniority_refines_search_title_once() -> None:
    plan = build_search_plan(goal(target_seniority="Senior"))

    assert plan.search_title == "Senior AI Solutions Architect"
    assert plan.direct_source_queries == [
        '"Senior AI Solutions Architect" "Toronto, ON" careers',
        '"Senior AI Solutions Architect" Toronto Ontario careers',
    ]
    assert plan.exact_queries == [
        '"Senior AI Solutions Architect" jobs "Toronto, ON"',
        '"Senior AI Solutions Architect" jobs Toronto Ontario',
    ]


def test_explicit_toronto_metro_scope_adds_only_bounded_grounded_variants() -> None:
    plan = build_search_plan(goal(geography_scopes=[GeographyScope.METRO_AREA]))

    assert [item.scope for item in plan.geography_queries] == [
        GeographyScope.METRO_AREA,
        GeographyScope.METRO_AREA,
        GeographyScope.METRO_AREA,
    ]
    assert [item.location_phrase for item in plan.geography_queries] == [
        '"Greater Toronto Area"',
        "Mississauga Ontario",
        "Markham Ontario",
    ]


def test_province_and_remote_scopes_are_never_added_implicitly() -> None:
    plan = build_search_plan(goal(preferred_work_modes=["Remote"]))

    assert GeographyScope.PROVINCE not in plan.allowed_geography_scopes
    assert GeographyScope.COUNTRY_REMOTE not in plan.allowed_geography_scopes


def test_canada_location_naturally_uses_country_scope() -> None:
    plan = build_search_plan(goal(target_location="Canada"))

    assert plan.allowed_geography_scopes == [GeographyScope.COUNTRY]
    assert plan.direct_source_queries == ['"AI Solutions Architect" Canada careers']
    assert plan.exact_queries == ['"AI Solutions Architect" jobs Canada']
    assert plan.target_title_variants == [
        "AI Solution Architect",
        "AI/ML Solutions Architect",
        "Generative AI Solutions Architect",
        "GenAI Solutions Architect",
    ]


def test_preferences_and_exclusions_are_retained_without_query_stuffing() -> None:
    plan = build_search_plan(
        goal(
            preferred_work_modes=["Remote"],
            target_industries=["Financial Services"],
            exclusions=["No contract roles"],
        )
    )

    assert plan.preferred_work_modes == ["Remote"]
    assert plan.target_industries == ["Financial Services"]
    assert plan.exclusions == ["No contract roles"]
    assert "Remote" not in plan.exact_queries[0]
    assert "contract" not in plan.exact_queries[0]


def test_no_target_returns_role_discovery_state_without_query() -> None:
    plan = build_search_plan(goal(goal_type=GoalType.CAREER_EXPLORATION, target_role=None))

    assert plan.status is SearchPlanStatus.SEARCH_PLAN_REQUIRES_ROLE_DISCOVERY
    assert plan.exact_queries == []


def test_unapproved_goal_is_rejected() -> None:
    with pytest.raises(MarketConfigurationError, match="approved career goal"):
        build_search_plan(
            CareerGoal(goal_type=GoalType.ROLE_TRANSITION, target_role="Data Engineer")
        )
