import pytest

from ai_career_navigator.domain import GoalType
from ai_career_navigator.goal import GOAL_INTENT_CONFIGS, goal_intent_config
from ai_career_navigator.ui.pages.goal import (
    _market_result_available,
    _safe_live_failure_message,
)


def test_configuration_preserves_all_six_domain_intents_for_saved_goals() -> None:
    assert tuple(GOAL_INTENT_CONFIGS) == (
        GoalType.CURRENT_MARKET_ANALYSIS,
        GoalType.ROLE_TRANSITION,
        GoalType.TARGET_CAREER_PATH,
        GoalType.LEADERSHIP_PROGRESSION,
        GoalType.CAREER_EXPLORATION,
        GoalType.CAREER_REASSESSMENT,
    )


def test_find_roles_now_asks_for_neither_target_nor_timeline() -> None:
    config = goal_intent_config(GoalType.CURRENT_MARKET_ANALYSIS)

    assert config.target_label == "Role to assess now (optional)"
    assert not config.show_timeline
    assert not config.show_bridge_willingness


def test_named_transition_requires_a_target_and_supports_path_preferences() -> None:
    config = goal_intent_config(GoalType.ROLE_TRANSITION)

    assert config.requires_target
    assert config.target_label == "Role you want to transition into"
    assert config.show_timeline
    assert config.show_bridge_willingness


def test_leadership_does_not_require_target_or_bridge_role() -> None:
    config = goal_intent_config(GoalType.LEADERSHIP_PROGRESSION)

    assert not config.requires_target
    assert config.target_label == "Leadership role or level (optional)"
    assert not config.show_bridge_willingness


def test_open_exploration_has_no_irrelevant_target_or_timeline() -> None:
    config = goal_intent_config(GoalType.CAREER_EXPLORATION)

    assert config.target_label is None
    assert not config.show_timeline
    assert not config.show_search_expansion


def test_unknown_goal_type_fails() -> None:
    with pytest.raises(ValueError, match="unsupported goal type"):
        goal_intent_config("Unknown")  # type: ignore[arg-type]


def test_live_workflow_surfaces_any_retrieved_market_snapshot() -> None:
    assert _market_result_available(
        {"workflow_status": "WAITING_FOR_HUMAN", "market_snapshot": object()}
    )
    assert _market_result_available({"workflow_status": "FAILED", "market_snapshot": object()})
    assert not _market_result_available({"workflow_status": "RUNNING", "market_snapshot": None})


def test_live_failure_messages_remain_safe_and_actionable() -> None:
    message = _safe_live_failure_message("AUTHENTICATION_ERROR")

    assert "credentials" in message
    assert "API" not in message


def test_market_transport_failure_is_not_presented_as_nvidia_failure() -> None:
    message = _safe_live_failure_message("MARKETTRANSPORTERROR")

    assert "market sources" in message
    assert "Model-based requirement extraction has not started" in message
    assert "NVIDIA" not in message


def test_interrupted_run_message_preserves_confirmed_inputs() -> None:
    message = _safe_live_failure_message("INTERRUPTED_RUN")

    assert "interrupted" in message
    assert "profile and goal are unchanged" in message
