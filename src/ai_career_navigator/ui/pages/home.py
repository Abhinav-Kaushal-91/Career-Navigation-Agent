"""Career Navigator landing view."""

import streamlit as st

from ai_career_navigator.ui.components.cards import render_card
from ai_career_navigator.ui.components.navigation import go_to, reset_demo, reset_workflow
from ai_career_navigator.ui.components.states import (
    render_empty_state,
    render_error_state,
    render_insufficient_evidence_state,
    render_loading_state,
    render_partial_evidence_state,
)


def render() -> None:
    st.caption("YOUR NEXT CHAPTER")
    st.title("Turn your experience into direction")
    st.write("Explore your options, understand your fit, and decide what to do next.")
    has_progress = st.session_state.highest_reached_step != "Home"
    primary, secondary, reset, _ = st.columns([1.4, 1.15, 1.15, 2.3])
    with primary:
        label = "Continue career analysis" if has_progress else "Build my career profile"
        if st.button(label, type="primary", use_container_width=True):
            if has_progress:
                go_to(st.session_state.highest_reached_step)
            else:
                reset_workflow("manual")
    with secondary:
        if st.button(
            "Explore demo",
            help=(
                "Load an editable Senior Java Developer test profile "
                "through Education & Certifications."
            ),
            use_container_width=True,
        ):
            reset_demo()
    with reset:
        if has_progress and st.button("Start new analysis", type="tertiary"):
            reset_workflow("manual")

    st.caption(
        "Explore demo prefills a test profile through Education. It replaces session progress; "
        "you choose when to run AI review and live analysis."
    )

    st.subheader("What Career Navigator helps you do")
    columns = st.columns(4)
    capabilities = (
        ("Explore directions", "Find a next role, change fields, or grow into leadership."),
        ("Understand the role", "See what employers ask for in the postings we find."),
        ("Know your fit", "Recognize your strengths and the gaps worth addressing."),
        ("Make a plan", "Follow specific next steps grounded in your assessment."),
    )
    for column, (title, body) in zip(columns, capabilities, strict=True):
        with column:
            render_card(title, body, height=170)

    st.caption(
        "You confirm your profile. We distinguish demonstrated skills from unanswered questions."
    )

    with st.expander("Preview honest system states"):
        render_loading_state()
        render_partial_evidence_state()
        render_insufficient_evidence_state()
        render_empty_state()
        render_error_state()
