"""Read-only production-page preview of a saved local-description backend run."""

import json
import sys
from pathlib import Path

import streamlit as st
from pydantic import TypeAdapter

from ai_career_navigator.orchestration.state import CareerGraphState
from ai_career_navigator.ui.components.navigation import initialize_session_state
from ai_career_navigator.ui.pages.assessment import render_assessment
from ai_career_navigator.ui.pages.live_views import render_live_plan

st.set_page_config(page_title="Career Navigator | Supplied descriptions", layout="wide")
initialize_session_state()
path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else None
if not path or not path.is_file():
    st.error("A saved backend results file is required.")
    st.stop()
report = json.loads(path.read_text(encoding="utf-8"))
state = TypeAdapter(CareerGraphState).validate_python(report["graph_state"])
st.sidebar.title("Career Navigator")
st.sidebar.caption("Saved-file test · Demo candidate")
if "preview_next_view" in st.session_state:
    st.session_state.preview_view = st.session_state.pop("preview_next_view")
page = st.sidebar.radio("View", ["Analysis", "Plan", "Input files"], key="preview_view")
st.session_state.current_step = page if page != "Input files" else "Analysis"
initial_step = st.session_state.current_step
st.sidebar.caption("Read-only results. Refreshing makes no model calls.")
st.sidebar.caption(f"Model calls: {report['model_calls']}")
st.sidebar.caption(f"Backend: {report['total_seconds']:.2f} seconds")
st.sidebar.caption("No plan approval or profile changes are saved here.")
with st.container(horizontal=True, horizontal_alignment="center"):
    with st.container(width=1120):
        st.info("Your saved job descriptions + the synthetic demo profile. No live job search.")
        if not report["model_calls"]:
            st.warning(
                "The current title filter selected 0 descriptions for the model. "
                "This is a selection-rule stop, not an LLM response or a candidate skill gap."
            )
        if page == "Analysis":
            render_assessment(state, evidence_label="Supplied-file backend result")
        elif page == "Plan":
            render_live_plan(state, evidence_label="Supplied-file backend result")
        else:
            st.title("The five supplied descriptions")
            st.table(
                [
                    {
                        "File": m["file"],
                        "Employer": m["employer"],
                        "Title": m["title"],
                        "Words": m["words"],
                        "Current classification": m["classification"],
                    }
                    for m in report["manifest"]
                ]
            )
            st.caption(
                "Classifications are the current application's output, not manual title overrides."
            )
            st.caption(
                "BMO's title comes from its filename; public posting links were not supplied."
            )
if st.session_state.current_step != initial_step:
    destination = st.session_state.current_step
    if destination in {"Analysis", "Plan"}:
        st.session_state.preview_next_view = destination
        st.rerun()
    else:
        st.info("Edit the profile or goal in the main app, not this saved-result view.")
