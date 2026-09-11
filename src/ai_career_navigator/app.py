"""Synthetic Streamlit product shell for the V1 journey."""

import streamlit as st

from ai_career_navigator.ui.components.navigation import (
    APP_VIEWS,
    initialize_session_state,
    render_app_navigation,
)
from ai_career_navigator.ui.pages import assessment, goal, home, plan, profile

st.set_page_config(
    page_title="Career Navigator", page_icon="CN", layout="wide", initial_sidebar_state="expanded"
)
initialize_session_state()

current_step = st.session_state.current_step
if current_step not in APP_VIEWS:
    current_step = "Home"
    st.session_state.current_step = current_step

render_app_navigation(current_step)

views = {
    "Home": home.render,
    "Profile": profile.render,
    "Goal": goal.render,
    "Market": assessment.render,
    "Analysis": assessment.render,
    "Plan": plan.render,
}
with st.container(horizontal=True, horizontal_alignment="center"):
    with st.container(width=1120):
        views[current_step]()
