"""Local, read-only presentation harness over serialized production-graph replays.

No providers or private profiles are loaded. These fixtures test browser rendering,
not live provider quality. Run from the project root with Streamlit.
"""

import json
from pathlib import Path

import streamlit as st
from pydantic import TypeAdapter

from ai_career_navigator.orchestration.state import CareerGraphState
from ai_career_navigator.ui.components.navigation import (
    initialize_session_state,
    render_app_navigation,
    surface_graph_workflow_state,
)
from ai_career_navigator.ui.pages.live_views import (
    render_live_analysis,
    render_live_market,
    render_live_plan,
)

st.set_page_config(page_title="Career Navigator — V1 validation", layout="wide")
initialize_session_state()
fixture_path = Path(__file__).resolve().parents[1] / (
    "outputs/v1-reliability-20260906/replay-results.json"
)
results = json.loads(fixture_path.read_text(encoding="utf-8"))["results"]
cases = {item["case_id"]: item for item in results}
case_choices = ["CURRENT-A", "TARGET-A", "REASSESS-A"]
live_path = fixture_path.with_name("live-current-a.json")
if live_path.is_file():
    cases["LIVE-CURRENT-A"] = json.loads(live_path.read_text(encoding="utf-8"))
    case_choices.append("LIVE-CURRENT-A")
case_id = st.sidebar.selectbox("Validation case", case_choices)
evidence_label = (
    "Captured live results for a synthetic profile — no new provider requests"
    if case_id == "LIVE-CURRENT-A"
    else "Frozen synthetic validation replay"
)
if st.session_state.get("validation_case_loaded") != case_id:
    state = TypeAdapter(CareerGraphState).validate_python(cases[case_id]["graph_state"])
    st.session_state.live_graph_state = state
    st.session_state.confirmed_profile = state["confirmed_profile"]
    st.session_state.confirmed_goal = state["confirmed_goal"]
    st.session_state.profile_confirmed = True
    st.session_state.goal_confirmed = True
    st.session_state.profile_input_mode = "validation"
    st.session_state.current_step = "Market"
    st.session_state.highest_reached_step = "Plan"
    st.session_state.validation_case_loaded = case_id
    st.session_state.plan_review_confirmation = False
    surface_graph_workflow_state(state)

st.info(
    f"Validation replay · {case_id} · {evidence_label}. "
    "Production page renderers; review actions affect this temporary QA session only."
)
current = st.session_state.current_step
render_app_navigation(current)
renderers = {
    "Market": render_live_market,
    "Analysis": render_live_analysis,
    "Plan": render_live_plan,
}
if current in renderers:
    renderers[current](st.session_state.live_graph_state, evidence_label=evidence_label)
else:
    st.info("This read-only harness covers Market, Analysis, and Plan. Select one in the sidebar.")
