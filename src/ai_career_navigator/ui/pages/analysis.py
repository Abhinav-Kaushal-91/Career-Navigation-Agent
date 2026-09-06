"""Candidate analysis page for live and explicitly synthetic workflows."""

import streamlit as st

from ai_career_navigator.ui.demo_data import (
    CANDIDATE_PROFILE,
    DEMO_CAREER_SYNTHESIS,
    DEMO_LABEL,
    DEMO_REQUIREMENT_SUMMARY,
    MARKET_SNAPSHOT,
    ROLE_ASSESSMENT,
)
from ai_career_navigator.ui.pages.live_views import render_live_analysis


def render() -> None:
    if st.session_state.profile_input_mode != "demo":
        render_live_analysis()
        return

    render_live_analysis(
        {
            "market_snapshot": MARKET_SNAPSHOT,
            "requirement_summary": DEMO_REQUIREMENT_SUMMARY,
            "role_assessment": ROLE_ASSESSMENT,
            "confirmed_profile": CANDIDATE_PROFILE,
            "career_assessment_synthesis": DEMO_CAREER_SYNTHESIS,
        },
        evidence_label=DEMO_LABEL,
    )
