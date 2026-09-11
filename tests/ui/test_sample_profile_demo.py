"""The home demo shortcut seeds inputs, never downstream answers or approvals."""

from pathlib import Path

import streamlit as st
from streamlit.testing.v1 import AppTest

from ai_career_navigator.domain import EvidenceMaturity
from ai_career_navigator.profile import ProfileDraft
from ai_career_navigator.ui.demo_data import sample_profile_draft
from ai_career_navigator.ui.pages import profile

APP = Path(__file__).parents[2] / "src" / "ai_career_navigator" / "app.py"


def test_review_displays_date_derived_experience_separately_from_self_report():
    app = AppTest.from_file(APP).run()
    click(app, "Explore demo")
    app.session_state["current_profile_step"] = "Review"
    app.session_state["highest_reached_profile_step"] = "Review"
    app.run()
    assert not app.exception
    assert "How professional experience is calculated" in [x.label for x in app.expander]
    text = " ".join(x.value for x in app.markdown)
    assert "years from employment dates" in text
    captions = " ".join(x.value for x in app.caption)
    assert "Overlapping jobs count once" in captions
    assert "Self-reported experience: 8 years" in captions


def click(app, label):
    next(button for button in app.button if button.label == label).click().run()
    assert not app.exception


def test_demo_loads_only_unconfirmed_inputs_through_education(monkeypatch):
    def no_live_call(*args, **kwargs):
        raise AssertionError("Loading sample inputs must not invoke a model or live workflow")

    monkeypatch.setattr(profile, "build_live_workflow_runtime", no_live_call)
    monkeypatch.setattr(profile, "_run_capability_inference", no_live_call)
    app = AppTest.from_file(APP).run()
    click(app, "Explore demo")
    state = app.session_state
    assert state["profile_input_mode"] == "manual"
    assert state["sample_profile_loaded"] is True
    assert state["current_step"] == state["highest_reached_step"] == "Profile"
    assert state["current_profile_step"] == state["highest_reached_profile_step"] == "Education"
    assert state["capability_inference_status"] == "NOT_STARTED"
    for key in (
        "confirmed_profile",
        "confirmed_goal",
        "goal_draft",
        "live_graph_state",
        "live_workflow_runtime",
        "capability_inference_result",
        "displayed_plan_id",
    ):
        assert state[key] is None
    assert not state["profile_confirmed"] and not state["goal_confirmed"]
    assert not state["live_analysis_requested"]
    draft = ProfileDraft.model_validate(state["profile_draft"])
    assert draft.about.current_role == "Senior Java Developer"
    assert draft.about.current_location == "Toronto, Canada"
    assert draft.about.career_summary and draft.core_competencies_text
    assert draft.experiences and draft.projects and draft.education and draft.certifications
    assert draft.skills == []  # Strengths are still for the user/model to review.
    assert draft.projects[0].maturity is EvidenceMaturity.DEMONSTRATED
    assert "Bachelor of Science" in " ".join(x.value for x in app.markdown)
    assert any(b.label == "Continue to AI Strength Identification" for b in app.button)


def test_sample_is_editable_and_normal_strengths_flow_starts_only_after_click(monkeypatch):
    calls = []

    def record_review(candidate):
        calls.append(candidate)
        st.session_state.capability_inference_status = "EMPTY"

    monkeypatch.setattr(profile, "_run_capability_inference", record_review)
    app = AppTest.from_file(APP).run()
    click(app, "Explore demo")
    assert not calls
    click(app, "1 About You")
    next(x for x in app.text_input if x.label == "Current role (optional)").set_value("Java Lead")
    click(app, "Save and continue")
    assert app.session_state["profile_draft"]["about"]["current_role"] == "Java Lead"
    assert not calls
    click(app, "4 Education")
    click(app, "Continue to AI Strength Identification")
    assert len(calls) == 1
    assert calls[0].current_role == "Java Lead"
    assert calls[0].professional_summary.startswith("SYNTHETIC TEST PROFILE")
    assert app.session_state["profile_input_mode"] == "manual"
    assert not app.session_state["goal_confirmed"]


def test_reloading_demo_clears_old_results_and_blank_profile_stays_blank():
    app = AppTest.from_file(APP).run()
    click(app, "Explore demo")
    old_id = app.session_state["profile_draft"]["experiences"][0]["entry_id"]
    app.session_state["current_step"] = "Home"
    app.session_state["highest_reached_step"] = "Plan"
    app.session_state["confirmed_goal"] = {"old": True}
    app.session_state["live_graph_state"] = {"old": True}
    app.session_state["displayed_plan_id"] = "old-plan"
    app.session_state["strengths_selection"] = ["Old capability"]
    app.run()
    click(app, "Explore demo")
    assert app.session_state["live_graph_state"] is None
    assert app.session_state["confirmed_goal"] is None
    assert app.session_state["displayed_plan_id"] is None
    assert "strengths_selection" not in app.session_state
    assert app.session_state["profile_draft"]["experiences"][0]["entry_id"] != old_id
    app.session_state["current_step"] = "Home"
    app.run()
    click(app, "Start new analysis")
    assert app.session_state["sample_profile_loaded"] is False
    assert ProfileDraft.model_validate(app.session_state["profile_draft"]) == ProfileDraft()
    assert app.session_state["current_profile_step"] == "About You"


def test_sample_factory_does_not_share_mutable_inputs():
    first, second = sample_profile_draft(), sample_profile_draft()
    first.experiences.clear()
    assert len(second.experiences) == 1
