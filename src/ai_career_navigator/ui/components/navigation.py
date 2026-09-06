"""Controlled synthetic workflow navigation."""

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass

import streamlit as st

WORKFLOW_STEPS = ("Profile", "Goal", "Market", "Analysis", "Plan")
APP_VIEWS = ("Home", *WORKFLOW_STEPS)
SESSION_DEFAULTS = {
    "current_step": "Home",
    "highest_reached_step": "Home",
    "profile_confirmed": False,
    "profile_input_mode": None,
    "current_profile_step": "About You",
    "highest_reached_profile_step": "About You",
    "profile_draft": None,
    "profile_new_form_versions": {
        "experience": 0,
        "skill": 0,
        "project": 0,
        "education": 0,
        "certification": 0,
    },
    "confirmed_profile": None,
    "capability_review_active": False,
    "capability_inference_status": "NOT_STARTED",
    "capability_inference_result": None,
    "capability_inference_error": None,
    "capability_inference_decisions": {},
    "capability_inference_metadata": None,
    "selected_goal_type": None,
    "goal_draft": None,
    "goal_review_ready": False,
    "goal_confirmed": False,
    "confirmed_goal": None,
    "inferred_capability_decision": None,
    "plan_decision": None,
    "displayed_plan_id": None,
    "displayed_plan_version": None,
    "selected_plan_review_action": None,
    "plan_review_confirmation": False,
    "graph_workflow_status": None,
    "graph_human_action_required": None,
    "graph_market_ready": False,
    "live_workflow_runtime": None,
    "live_thread_id": None,
    "live_graph_state": None,
    "live_graph_interrupts": (),
    "live_workflow_error": None,
    "live_analysis_requested": False,
    "live_analysis_running": False,
    "live_analysis_completed_stages": 0,
}


def initialize_session_state() -> None:
    """Initialize independent copies of mutable temporary UI defaults."""

    for key, value in SESSION_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = deepcopy(value)


def surface_graph_workflow_state(state: dict[str, object]) -> None:
    """Copy only presentation-safe graph status into temporary Streamlit state."""

    status = state.get("workflow_status")
    action = state.get("human_action_required")
    stage = state.get("current_stage")
    st.session_state.graph_workflow_status = getattr(status, "value", status)
    st.session_state.graph_human_action_required = getattr(action, "value", action)
    st.session_state.graph_market_ready = getattr(stage, "value", stage) in {
        "MARKET_READY",
        "CANDIDATE_REQUIREMENT_COMPARISON",
        "CANDIDATE_COMPARISON_READY",
        "GAP_AND_ACCESSIBILITY_ANALYSIS",
        "CANDIDATE_ASSESSMENT_READY",
        "BRIDGE_ROLE_ASSESSMENT",
        "TIMELINE_ASSESSMENT",
        "CAREER_PATH_ASSESSMENT_READY",
        "CAREER_PLAN_GENERATION",
        "CAREER_PLAN_READY",
    }


@dataclass(frozen=True)
class StepState:
    label: str
    number: int
    status: str
    available: bool


def _view_index(view: str) -> int:
    if view not in APP_VIEWS:
        raise ValueError(f"unknown UI view: {view}")
    return APP_VIEWS.index(view)


def next_highest_reached(highest: str, destination: str) -> str:
    """Advance reached-state monotonically; Home never resets progress."""

    return destination if _view_index(destination) > _view_index(highest) else highest


def can_navigate(destination: str, highest: str) -> bool:
    """Allow Home and workflow views that have already been reached."""

    return destination == "Home" or _view_index(destination) <= _view_index(highest)


def workflow_step_states(current: str, highest: str | None = None) -> tuple[StepState, ...]:
    """Return accessible state for each workflow step."""

    current_index = _view_index(current)
    highest_index = _view_index(highest or current)
    return tuple(
        StepState(
            label=label,
            number=index,
            status=(
                "current"
                if index == current_index
                else "complete"
                if index < current_index
                else "available"
                if index <= highest_index
                else "upcoming"
            ),
            available=index <= highest_index,
        )
        for index, label in enumerate(APP_VIEWS[1:], start=1)
    )


def go_to(view: str) -> None:
    """Move within the synthetic shell without discarding temporary state."""

    _view_index(view)
    highest = st.session_state.get("highest_reached_step", "Home")
    st.session_state.highest_reached_step = next_highest_reached(highest, view)
    st.session_state.current_step = view
    st.rerun()


def reset_workflow(profile_mode: str) -> None:
    """Explicitly clear temporary workflow state for manual or demo onboarding."""

    for key, value in SESSION_DEFAULTS.items():
        st.session_state[key] = deepcopy(value)
    st.session_state.profile_input_mode = profile_mode
    go_to("Profile")


def reset_demo() -> None:
    """Begin a fresh, clearly labeled synthetic demonstration."""

    reset_workflow("demo")


def invalidate_workflow_after_goal_change() -> None:
    """Discard results derived from an old goal while preserving profile and goal draft data."""

    for key in (
        "live_thread_id",
        "live_graph_state",
        "live_graph_interrupts",
        "live_workflow_error",
        "live_analysis_requested",
        "live_analysis_running",
        "live_analysis_completed_stages",
        "graph_workflow_status",
        "graph_human_action_required",
        "plan_decision",
        "displayed_plan_id",
        "displayed_plan_version",
        "selected_plan_review_action",
    ):
        st.session_state[key] = deepcopy(SESSION_DEFAULTS[key])
    st.session_state.graph_market_ready = False
    st.session_state.highest_reached_step = "Goal"


def render_app_navigation(current: str) -> None:
    """Render the native Streamlit stage rail from the approved handoff."""

    highest = st.session_state.highest_reached_step
    profile = st.session_state.get("confirmed_profile")
    approved_count = 0
    if profile is not None:
        approved = getattr(profile, "approved_evidence_items", None)
        if approved is None and isinstance(profile, dict):
            approved = [
                item for item in profile.get("evidence_items", []) if item.get("approved_by_user")
            ]
        approved_count = len(approved or ())
    graph_state = st.session_state.get("live_graph_state")
    role = graph_state.get("role_assessment") if isinstance(graph_state, dict) else None
    gap_count = len(getattr(role, "gaps", ())) if role is not None else 0
    completeness = min(1.0, approved_count / 14) if approved_count else 0.0

    analysis_active = bool(
        st.session_state.get("live_analysis_requested")
        or st.session_state.get("live_analysis_running")
    )

    with st.sidebar:
        st.title("Career Navigator")
        st.caption("Evidence-grounded career strategy")
        st.divider()
        selected = st.radio(
            "Stage",
            APP_VIEWS,
            index=APP_VIEWS.index(current),
            key=f"stage_navigation_{current.lower()}",
            disabled=analysis_active,
        )
        if selected != current:
            if can_navigate(selected, highest):
                go_to(selected)
            else:
                # An unreached page may show its honest empty state, but selecting it
                # does not advance workflow state or run business logic.
                st.session_state.current_step = selected
                st.rerun()
        if analysis_active:
            st.caption("Navigation is paused while this analysis run is active.")
        st.divider()
        st.write("Profile completeness")
        st.progress(
            completeness,
            text=f"{round(completeness * 100)}% · {approved_count} confirmed items",
        )
        if gap_count:
            st.caption(f"{gap_count} open gap(s)")
        if st.session_state.get("profile_input_mode") == "demo":
            st.badge("Synthetic data", color="orange")
            st.badge("Demo mode", color="blue")
            st.caption("Nothing is saved in demo mode.")


def render_workflow_actions(
    *, back_label: str, back_view: str, primary_label: str, on_primary: Callable[[], None]
) -> None:
    """Render the consistent bottom navigation pattern."""

    back, _, primary = st.columns([1.25, 2.5, 1.65])
    with back:
        if st.button(back_label, key=f"back_{back_view.lower()}", use_container_width=True):
            go_to(back_view)
    with primary:
        if st.button(
            primary_label,
            key=f"primary_{primary_label.lower().replace(' ', '_')}",
            type="primary",
            use_container_width=True,
        ):
            on_primary()
