"""Isolated synthetic UI QA; no credentials, retrieval, LLM calls or profile mutation."""

from types import SimpleNamespace

import streamlit as st

from ai_career_navigator.ui.components.career_visuals import (
    render_competency_snapshot,
    render_path_map,
)
from ai_career_navigator.ui.demo_data import visual_snapshot_example

st.set_page_config(page_title="Career Navigator | Visual QA", layout="wide")
st.caption("SYNTHETIC DESIGN CHECK — NOT A LIVE CAREER ASSESSMENT")
with st.container(horizontal=True, horizontal_alignment="center"):
    with st.container(width=1120):
        rows, dimensions = visual_snapshot_example()
        render_competency_snapshot(rows, dimensions)
        st.subheader("How you compare")
        st.table(rows)
        count = st.selectbox("Preview actual step count", [1, 2, 5, 8], index=2)
        kinds = ["EVIDENCE", "SKILL", "PROJECT", "REASSESSMENT", "APPLICATION_READINESS"]
        milestones = [SimpleNamespace(milestone_type=kinds[i % len(kinds)]) for i in range(count)]
        render_path_map(SimpleNamespace(target_role="Your chosen role", milestones=milestones))
