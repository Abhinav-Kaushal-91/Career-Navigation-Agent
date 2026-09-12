"""Read-only production rendering of an existing audit; no new provider calls."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import streamlit as st

from ai_career_navigator.career.leadership import LeadershipAssessment
from ai_career_navigator.career.same_role import SameRoleAssessment
from ai_career_navigator.career.transition import TransitionAssessment
from ai_career_navigator.domain import CareerPlan, GoalType
from ai_career_navigator.ui.pages.same_role import render_same_role_analysis, render_same_role_plan

st.set_page_config(page_title="Career Navigator | Saved result review", layout="wide")
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
version = data["assessment"]["rule_version"]
model = (
    LeadershipAssessment
    if version.startswith("leadership-")
    else (TransitionAssessment if version.startswith("career-transition-") else SameRoleAssessment)
)
assessment = model.model_validate(data["assessment"])
plan = CareerPlan.model_validate(data["plan"]) if data.get("plan") else None
state = {
    "transition_assessment": assessment,
    "career_plan": plan,
    "confirmed_goal": SimpleNamespace(
        target_role=plan.target_role if plan else "Target role",
        target_location="Saved search",
        goal_type=GoalType(data["goal_type"]),
    ),
}
st.caption("SAVED LIVE RESULT · Read-only display check · No job search or model calls")
page = st.radio("Page", ["Analysis", "Plan"], horizontal=True)
with st.container(horizontal=True, horizontal_alignment="center"):
    with st.container(width=1120):
        if page == "Analysis":
            st.title("Your career assessment")
            render_same_role_analysis(state)
        else:
            render_same_role_plan(state, read_only=True)
