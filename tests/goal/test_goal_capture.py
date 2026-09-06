from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from ai_career_navigator.domain import (
    ApprovalStatus,
    CandidateProfile,
    CareerGoal,
    CareerStage,
    GoalType,
)
from ai_career_navigator.goal import (
    GoalDraft,
    GoalValidationError,
    build_career_goal,
    confirm_career_goal,
    format_goal_review,
    goal_intent_config,
)

NOW = datetime(2026, 9, 3, 16, 0, tzinfo=UTC)


def test_current_market_goal_without_target_is_valid() -> None:
    goal = build_career_goal(GoalDraft(goal_type=GoalType.CURRENT_MARKET_ANALYSIS))

    assert goal.target_role is None
    assert not goal.exploration_mode


def test_open_exploration_without_target_is_valid_end_to_end() -> None:
    draft = GoalDraft(
        goal_type=GoalType.CAREER_EXPLORATION,
        target_location="Canada",
        preferred_work_modes=["Remote"],
    )

    goal = confirm_career_goal(draft, now=NOW)

    assert goal.target_role is None
    assert goal.exploration_mode
    assert goal.approval_status is ApprovalStatus.APPROVED


def test_target_path_requires_and_preserves_target_role() -> None:
    with pytest.raises(GoalValidationError, match="target role"):
        build_career_goal(GoalDraft(goal_type=GoalType.TARGET_CAREER_PATH))

    goal = build_career_goal(
        GoalDraft(
            goal_type=GoalType.TARGET_CAREER_PATH,
            target_role="AI Solutions Architect",
        )
    )
    assert goal.target_role == "AI Solutions Architect"


def test_named_transition_ui_policy_requires_target_without_blanket_domain_rule() -> None:
    with pytest.raises(GoalValidationError, match="target role"):
        build_career_goal(GoalDraft(goal_type=GoalType.ROLE_TRANSITION))

    assert CareerGoal(goal_type=GoalType.ROLE_TRANSITION).target_role is None


@pytest.mark.parametrize("months", (-1, 0))
def test_nonpositive_timeline_fails(months: int) -> None:
    with pytest.raises(ValidationError):
        GoalDraft(goal_type=GoalType.CAREER_EXPLORATION, target_timeline_months=months)


def test_approved_goal_requires_timezone_aware_approved_at() -> None:
    with pytest.raises(ValidationError, match="approved_at"):
        CareerGoal(
            goal_type=GoalType.CURRENT_MARKET_ANALYSIS,
            approval_status=ApprovalStatus.APPROVED,
        )

    goal = confirm_career_goal(GoalDraft(goal_type=GoalType.CURRENT_MARKET_ANALYSIS), now=NOW)
    assert goal.approved_at == NOW
    assert goal.approved_at.tzinfo is not None


def test_preferences_are_preserved_and_deduplicated_conservatively() -> None:
    draft = GoalDraft(
        goal_type=GoalType.CAREER_EXPLORATION,
        preferred_work_modes=["Remote", " remote ", "Hybrid"],
        target_industries=["Technology", "technology", "Financial Services"],
        bridge_role_willingness=None,
        search_expansion_permission=True,
        exclusions=["No relocation", " no relocation ", "No contract roles"],
    )
    goal = build_career_goal(draft)

    assert goal.preferred_work_modes == ["Remote", "Hybrid"]
    assert goal.target_industries == ["Technology", "Financial Services"]
    assert goal.exclusions == ["No relocation", "No contract roles"]
    assert goal.bridge_role_willingness is None
    assert goal.search_expansion_permission


def test_no_preference_replaces_specific_work_modes_and_industries() -> None:
    draft = GoalDraft(
        goal_type=GoalType.CAREER_EXPLORATION,
        preferred_work_modes=["Remote", "Flexible / No preference"],
        target_industries=["Technology", "No preference"],
    )

    assert draft.preferred_work_modes == ["Flexible / No preference"]
    assert draft.target_industries == ["No preference"]


def test_optional_target_leadership_and_reassessment_goals_build() -> None:
    leadership = build_career_goal(GoalDraft(goal_type=GoalType.LEADERSHIP_PROGRESSION))
    reassessment = build_career_goal(
        GoalDraft(
            goal_type=GoalType.CAREER_REASSESSMENT,
            target_timeline_months=12,
            target_location="Toronto, Canada",
        )
    )

    assert leadership.target_role is None
    assert reassessment.target_timeline_months == 12


def test_review_uses_friendly_labels_instead_of_enum_values() -> None:
    draft = GoalDraft(
        goal_type=GoalType.TARGET_CAREER_PATH,
        target_role="AI Solutions Architect",
        target_timeline_months=24,
        bridge_role_willingness=True,
        search_expansion_permission=True,
    )
    rows = dict(format_goal_review(draft))

    assert rows["Direction"] == "Plan toward a target role"
    assert rows["Timeline"] == "24 months"
    assert rows["Bridge role"] == "Open to an intermediate role"
    assert rows["Related-title expansion"] == "Allowed"


def test_goal_edit_round_trip_and_confirmation_do_not_modify_profile() -> None:
    profile = CandidateProfile(
        career_stage=CareerStage.STUDENT,
        approval_status=ApprovalStatus.APPROVED,
        created_at=NOW,
        confirmed_at=NOW,
    )
    original_profile = profile.model_dump(mode="json")
    draft = GoalDraft(
        goal_type=GoalType.CAREER_EXPLORATION,
        target_location="Canada",
    )
    restored = GoalDraft.model_validate(draft.model_dump(mode="json"))
    edited = restored.model_copy(update={"target_location": "Toronto, Canada"})

    goal = confirm_career_goal(edited, now=NOW)

    assert goal.goal_version == 1
    assert goal.target_location == "Toronto, Canada"
    assert profile.model_dump(mode="json") == original_profile


def test_conditional_field_policy_matches_each_goal_path() -> None:
    current = goal_intent_config(GoalType.CURRENT_MARKET_ANALYSIS)
    transition = goal_intent_config(GoalType.ROLE_TRANSITION)
    target = goal_intent_config(GoalType.TARGET_CAREER_PATH)
    leadership = goal_intent_config(GoalType.LEADERSHIP_PROGRESSION)
    exploration = goal_intent_config(GoalType.CAREER_EXPLORATION)
    reassessment = goal_intent_config(GoalType.CAREER_REASSESSMENT)

    assert current.target_label == "Role to assess now (optional)"
    assert not current.requires_target and not current.show_timeline
    assert transition.requires_target and transition.show_bridge_willingness
    assert target.requires_target and target.show_search_expansion
    assert leadership.target_label and not leadership.requires_target
    assert exploration.target_label is None and not exploration.show_timeline
    assert reassessment.target_label and reassessment.show_timeline


def test_goal_review_omits_bridge_and_expansion_when_they_do_not_apply() -> None:
    rows = dict(
        format_goal_review(
            GoalDraft(
                goal_type=GoalType.CURRENT_MARKET_ANALYSIS,
                target_role="Automation Developer",
            )
        )
    )

    assert "Bridge role" not in rows
    assert "Related-title expansion" not in rows
    assert "Timeline" not in rows


def test_open_exploration_review_does_not_claim_a_target() -> None:
    rows = dict(format_goal_review(GoalDraft(goal_type=GoalType.CAREER_EXPLORATION)))

    assert "Target" not in rows
    assert "Target seniority" not in rows
    assert "Bridge role" not in rows
