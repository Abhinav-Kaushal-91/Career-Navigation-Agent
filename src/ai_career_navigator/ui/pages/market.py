"""Market page for live and explicitly synthetic workflows."""

import streamlit as st

from ai_career_navigator.ui.demo_data import (
    DEMO_LABEL,
    DEMO_REQUIREMENT_SUMMARY,
    MARKET_SNAPSHOT,
)
from ai_career_navigator.ui.pages.live_views import render_live_market


def render() -> None:
    if st.session_state.profile_input_mode != "demo":
        render_live_market()
        return

    render_live_market(
        {
            "market_snapshot": MARKET_SNAPSHOT,
            "requirement_summary": DEMO_REQUIREMENT_SUMMARY,
        },
        evidence_label=DEMO_LABEL,
    )
