"""Offline synthetic service replay for visually checking the production renderers."""

import sys
from pathlib import Path

import streamlit as st

from ai_career_navigator.ui.components.navigation import initialize_session_state
from ai_career_navigator.ui.pages.assessment import render_assessment
from ai_career_navigator.ui.pages.live_views import render_live_plan

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests.market.test_five_posting_batch import completed_batch_state  # noqa: E402

st.set_page_config(page_title="Five-description assessment QA", layout="wide")
initialize_session_state()
if "batch_qa_state" not in st.session_state:
    st.session_state.batch_qa_state = completed_batch_state()
st.sidebar.title("Career Navigator")
page = st.sidebar.radio("Page", ["Analysis", "Plan"])
st.info("Synthetic five-description service replay. No live provider calls or real market verdict.")
with st.container(horizontal=True, horizontal_alignment="center"):
    with st.container(width=1120):
        if page == "Analysis":
            render_assessment(st.session_state.batch_qa_state)
        else:
            render_live_plan(st.session_state.batch_qa_state)
