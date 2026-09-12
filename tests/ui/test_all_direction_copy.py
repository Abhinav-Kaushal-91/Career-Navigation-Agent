"""All goal categories share presentation, never a hard-coded example conclusion."""

from types import SimpleNamespace

import pytest
from streamlit.testing.v1 import AppTest

from ai_career_navigator.domain import GoalType
from ai_career_navigator.ui.direction_copy import DIRECTION_COPY, direction_caption
from ai_career_navigator.ui.pages.same_role import comparison_rows
from tests.ui.test_review_presentation import assessment


@pytest.mark.parametrize("goal_type", list(GoalType))
def test_all_six_categories_render_shared_legacy_view_without_changing_result(goal_type):
    app = AppTest.from_string(f'''
from ai_career_navigator.domain import GoalType
from tests.market.test_five_posting_batch import completed_batch_state
from ai_career_navigator.ui.pages.assessment import render_assessment
from types import SimpleNamespace
state = completed_batch_state()
state["confirmed_goal"] = SimpleNamespace(goal_type=GoalType("{goal_type.value}"))
render_assessment(state)
''').run(timeout=20)
    assert not app.exception
    assert DIRECTION_COPY[goal_type] in [c.value for c in app.caption]
    assert "How you compare" in [s.value for s in app.subheader]
    assert list(app.table[0].value.columns) == ["Competency", "Your position"]
    assert app.table[0].value["Competency"].tolist() == [
        "Java", "SQL", "Automated Testing", "AWS (additional advantage)",
    ]
    assert "A credible leadership direction" not in [s.value for s in app.subheader]
    assert [e.label for e in app.expander] == ["Run details"]


@pytest.mark.parametrize("goal_type", list(GoalType))
def test_all_direction_plan_copy_keeps_actual_actions_and_approval_notice(goal_type):
    app = AppTest.from_string(f'''
from types import SimpleNamespace
from tests.ui.test_review_presentation import assessment
from ai_career_navigator.domain import GoalType, PlanStatus
from ai_career_navigator.ui.pages.same_role import render_same_role_plan
plan = SimpleNamespace(current_role="Current role", target_role="Chosen role",
    plan_status=PlanStatus.DRAFT, timing_basis="No fixed timeline",
    milestones=[SimpleNamespace(phase="Step 1", basis="Existing finding",
        action="Check the specific prerequisite before deciding.",
        measurable_outcome="The prerequisite is verified.")])
render_same_role_plan({{"same_role_assessment": assessment(), "career_plan": plan,
    "confirmed_goal": SimpleNamespace(goal_type=GoalType("{goal_type.value}"))}}, read_only=True)
''').run()
    assert not app.exception
    assert DIRECTION_COPY[goal_type] in [c.value for c in app.caption]
    assert any("Check the specific prerequisite before deciding." == m.value for m in app.markdown)
    assert any("Approval applies to this exact plan version" in c.value for c in app.caption)
    assert any("No fixed timeline" in c.value for c in app.caption)


def test_scope_and_status_are_not_inferred_from_example_role_or_positive_bias():
    original = assessment()
    core = original.competencies[0]
    core.name = "Welding safety"
    core.status = "PARTIALLY_DEMONSTRATED"
    assert comparison_rows(original) == [
        {"Competency": "Welding safety", "Your position": "Partially demonstrated"}
    ]
    original.competencies[1].expectation = "PREREQUISITE"
    assert len(comparison_rows(original)) == 2  # specialist eligibility is not erased
    core.status = "TRANSFERABLE"
    assert comparison_rows(original)[0]["Your position"] == "Transferable"
    core.status = "NOT_ESTABLISHED"
    assert comparison_rows(original)[0]["Your position"] == "Unconfirmed"
    assert len(original.competencies) == 2
    assert direction_caption(SimpleNamespace(goal_type=None)) == ""


def test_all_model_writing_paths_use_shared_role_neutral_style():
    from ai_career_navigator.career import (
        leadership,
        plan_prompts,
        same_role,
        synthesis_prompts,
        transition_prompts,
    )
    from ai_career_navigator.career.presentation_prompts import PLAIN_LANGUAGE_STYLE

    for module in (leadership, plan_prompts, same_role, synthesis_prompts, transition_prompts):
        assert PLAIN_LANGUAGE_STYLE in module.SYSTEM_PROMPT
    assert set(DIRECTION_COPY) == set(GoalType)
