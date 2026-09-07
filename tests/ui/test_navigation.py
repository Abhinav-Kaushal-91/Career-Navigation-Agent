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


def test_sidebar_evidence_count_is_not_an_arbitrary_completeness_percentage() -> None:
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_string(
        "from ai_career_navigator.ui.components.navigation import "
        "initialize_session_state, render_app_navigation\n"
        "initialize_session_state()\n"
        "render_app_navigation('Home')\n"
    ).run()
    assert not app.exception
    assert any("0 confirmed items" in item.value for item in app.caption)
    assert not any("Profile completeness" in item.value for item in app.markdown)
    assert not app.get("progress")


def test_frequency_axis_never_labels_more_than_one_hundred_percent() -> None:
    from ai_career_navigator.ui.components.charts import build_requirement_frequency_figure

    figure = build_requirement_frequency_figure([("Python", 1.0, 5, 5)])
    assert max(figure.layout.xaxis.tickvals) == 1


def test_frequency_categories_have_explicit_and_automatic_label_margins():
    from ai_career_navigator.ui.components.charts import build_requirement_frequency_figure

    figure = build_requirement_frequency_figure([("Automated Testing", 1.0, 5, 5)])
    assert figure.layout.margin.l >= 132
    assert figure.layout.margin.b >= 30
    assert figure.layout.yaxis.automargin is True
    assert list(figure.data[0].y) == ["Automated Testing"]


def test_employer_donut_uses_wrapping_native_caption_not_clipped_side_legend(monkeypatch):
    from streamlit.testing.v1 import AppTest

    from ai_career_navigator.ui.components import charts

    figures = []
    monkeypatch.setattr(charts, "_render_figure", figures.append)
    app = AppTest.from_string(
        "from ai_career_navigator.ui.components.charts import render_donut\n"
        "render_donut('Employers', 'Known employers', .6, "
        "'Top 3 employers', 'Other employers', sample_size=5)\n"
    ).run()
    assert not app.exception
    assert figures[0].layout.showlegend is False
    assert any(
        "Top 3 employers: 60%" in item.value and "Other employers: 40%" in item.value
        for item in app.caption
    )
