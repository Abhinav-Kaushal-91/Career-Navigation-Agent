"""Career-plan page for live and explicitly synthetic workflows."""

import streamlit as st

from ai_career_navigator.ui.demo_data import (
    BRIDGE_ASSESSMENT,
    CAREER_PLAN,
    DEMO_CAREER_SYNTHESIS,
    DEMO_LABEL,
    DEMO_REQUIREMENT_SUMMARY,
    ROLE_ASSESSMENT,
)
from ai_career_navigator.ui.pages.live_views import render_live_plan


def render() -> None:
    if st.session_state.profile_input_mode != "demo":
        render_live_plan()
        return

    render_live_plan(
        {
            "career_plan": CAREER_PLAN,
            "role_assessment": ROLE_ASSESSMENT,
            "requirement_summary": DEMO_REQUIREMENT_SUMMARY,
            "bridge_outcome": BRIDGE_ASSESSMENT.outcome,
            "career_assessment_synthesis": DEMO_CAREER_SYNTHESIS,
        },
        evidence_label=DEMO_LABEL,
    )
