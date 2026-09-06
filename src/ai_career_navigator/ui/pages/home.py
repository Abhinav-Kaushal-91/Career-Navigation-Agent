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
    st.title("Career Navigator")
    st.write(
        "Build a structured career profile, then compare your experience with current "
        "job-market evidence."
    )
    st.caption("Every figure is labelled with its source and confidence.")
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
        if st.button("Explore demo", use_container_width=True):
            reset_demo()
    with reset:
        if has_progress and st.button("Start new analysis", type="tertiary"):
            reset_workflow("manual")

    st.subheader("What Career Navigator helps you do")
    columns = st.columns(4)
    capabilities = (
        ("Explore roles", "Credible destinations built from confirmed evidence, not guesses."),
        ("Understand market", "Review postings, employers, scope, and stated limitations."),
        ("Identify gaps", "See readiness by dimension and what can close each gap."),
        ("Build your path", "Compare routes and turn the analysis into measurable milestones."),
    )
    for column, (title, body) in zip(columns, capabilities, strict=True):
        with column:
            render_card(title, body, height=205)

    st.info(
        "**Every number carries its source.** Figures are labelled validated, inferred, or "
        "synthetic. Confidence is shown next to the claim, never hidden in a footnote."
    )
    labels = st.columns(3)
    labels[0].badge("Validated", color="green")
    labels[1].badge("Inferred", color="orange")
    labels[2].badge("Synthetic", color="blue")

    with st.expander("Preview honest system states"):
        render_loading_state()
        render_partial_evidence_state()
        render_insufficient_evidence_state()
        render_empty_state()
        render_error_state()
