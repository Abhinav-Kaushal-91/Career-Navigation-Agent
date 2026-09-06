import pytest

from ai_career_navigator.ui.components.navigation import (
    SESSION_DEFAULTS,
    WORKFLOW_STEPS,
    can_navigate,
    next_highest_reached,
    workflow_step_states,
)


def test_workflow_steps_follow_v1_sequence() -> None:
    assert WORKFLOW_STEPS == ("Profile", "Goal", "Market", "Analysis", "Plan")


def test_workflow_step_states_mark_progress() -> None:
    states = workflow_step_states("Market", "Market")

    assert tuple(state.status for state in states) == (
        "complete",
        "complete",
        "current",
        "upcoming",
        "upcoming",
    )


def test_unknown_workflow_step_fails() -> None:
    with pytest.raises(ValueError):
        workflow_step_states("Unknown")


def test_backward_navigation_is_permitted() -> None:
    assert can_navigate("Profile", "Market")
    assert can_navigate("Goal", "Market")


def test_forward_navigation_respects_reached_state() -> None:
    assert can_navigate("Analysis", "Analysis")
    assert not can_navigate("Plan", "Analysis")


def test_home_is_distinct_from_resetting_progress() -> None:
    assert can_navigate("Home", "Analysis")
    assert next_highest_reached("Analysis", "Home") == "Analysis"


def test_highest_reached_does_not_decrease_when_navigating_backward() -> None:
    assert next_highest_reached("Plan", "Goal") == "Plan"


def test_graph_status_has_separate_temporary_ui_fields() -> None:
    assert SESSION_DEFAULTS["graph_workflow_status"] is None
    assert SESSION_DEFAULTS["graph_human_action_required"] is None
    assert SESSION_DEFAULTS["graph_market_ready"] is False
    assert SESSION_DEFAULTS["live_workflow_runtime"] is None
    assert SESSION_DEFAULTS["live_graph_state"] is None
    assert SESSION_DEFAULTS["live_workflow_error"] is None
    assert SESSION_DEFAULTS["live_analysis_requested"] is False
    assert SESSION_DEFAULTS["live_analysis_running"] is False
    assert SESSION_DEFAULTS["live_analysis_completed_stages"] == 0
    assert SESSION_DEFAULTS["profile_new_form_versions"] == {
        "experience": 0,
        "skill": 0,
        "project": 0,
        "education": 0,
        "certification": 0,
    }
