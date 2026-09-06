from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from ai_career_navigator.ui.demo_data import CAREER_PLAN


@pytest.mark.parametrize("view", ["Market", "Analysis", "Plan"])
def test_demo_visual_stages_render_without_exceptions(view: str) -> None:
    app_path = Path(__file__).parents[2] / "src" / "ai_career_navigator" / "app.py"
    app = AppTest.from_file(app_path).run()
    app.session_state["current_step"] = view
    app.session_state["highest_reached_step"] = "Plan"
    app.session_state["profile_input_mode"] = "demo"

    app = app.run()

    assert not app.exception


def test_demo_plan_uses_only_engine_supported_paths_without_probabilities() -> None:
    app_path = Path(__file__).parents[2] / "src" / "ai_career_navigator" / "app.py"
    app = AppTest.from_file(app_path).run()
    app.session_state["current_step"] = "Plan"
    app.session_state["highest_reached_step"] = "Plan"
    app.session_state["profile_input_mode"] = "demo"

    app = app.run()

    path_buttons = [
        button for button in app.button if str(button.key).startswith("select_live_path_")
    ]
    rendered_text = " ".join(
        item.value
        for collection in (app.markdown, app.caption, app.subheader)
        for item in collection
    )

    assert len(path_buttons) == len(CAREER_PLAN.bridge_roles)
    assert "Likelihood" not in rendered_text
