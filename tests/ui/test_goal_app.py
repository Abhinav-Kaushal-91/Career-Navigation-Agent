from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from ai_career_navigator.domain import GoalType
from ai_career_navigator.ui.demo_data import CAREER_GOAL


def goal_app() -> AppTest:
    app_path = Path(__file__).parents[2] / "src" / "ai_career_navigator" / "app.py"
    app = AppTest.from_file(app_path).run()
    app.session_state["current_step"] = "Goal"
    app.session_state["highest_reached_step"] = "Goal"
    app.session_state["profile_input_mode"] = "manual"
    return app.run()


@pytest.mark.parametrize("goal_type", tuple(GoalType))
def test_each_goal_type_renders_through_owned_selection_key(goal_type: GoalType) -> None:
    app = goal_app()
    key = f"choose_goal_{goal_type.value.lower()}"

    next(button for button in app.button if button.key == key).click().run()

    assert not app.exception
    assert app.session_state["selected_goal_type"] == goal_type.value


def test_open_exploration_hides_target_and_timeline_fields() -> None:
    app = goal_app()
    key = "choose_goal_career_exploration"
    next(button for button in app.button if button.key == key).click().run()

    assert "Target role" not in {item.label for item in app.text_input}
    assert "Desired timeline" not in {item.label for item in app.selectbox}


def test_active_live_run_renders_dedicated_progress_screen() -> None:
    app = goal_app()
    app.session_state["goal_confirmed"] = True
    app.session_state["confirmed_goal"] = CAREER_GOAL.model_dump(mode="json")
    app.session_state["live_analysis_requested"] = True
    app.session_state["live_analysis_running"] = True
    app.session_state["live_analysis_completed_stages"] = 3

    app = app.run()

    assert not app.exception
    assert any(title.value == "Building your career analysis…" for title in app.title)
    assert app.session_state["live_analysis_completed_stages"] == 3
    assert app.session_state["live_analysis_requested"] is False
    assert app.session_state["live_analysis_running"] is False
    assert app.session_state["live_workflow_error"] == "INTERRUPTED_RUN"
    assert app.radio[0].disabled
