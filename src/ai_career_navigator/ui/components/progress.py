"""Stage-based live-analysis progress presentation."""

import streamlit as st

LIVE_ANALYSIS_STAGES = (
    "Reviewing your confirmed profile",
    "Identifying your strengths",
    "Searching the current market",
    "Extracting employer requirements",
    "Comparing your experience",
    "Building your career path",
    "Preparing your career plan",
)

_COMPLETED_AFTER_NODE = {
    "initialize_run": 0,
    "profile_ready": 1,
    "capability_inference": 2,
    "goal_ready": 2,
    "market_retrieval": 3,
    "market_processing": 4,
    "market_ready": 4,
    "candidate_requirement_comparison": 5,
    "gap_and_accessibility_analysis": 5,
    "bridge_role_assessment": 5,
    "timeline_assessment": 6,
    "career_plan_generation": 7,
    "final_plan_review": 7,
}


def completed_stage_count(node_name: str | None) -> int:
    """Map an internal graph completion to a user-facing stage count."""

    return _COMPLETED_AFTER_NODE.get(node_name or "", 0)


def render_live_analysis_progress(
    completed_count: int,
    *,
    failed: bool = False,
    limited: bool = False,
) -> None:
    """Render real stage progress without exposing graph implementation names."""

    total = len(LIVE_ANALYSIS_STAGES)
    completed = max(0, min(completed_count, total))
    st.progress(completed / total, text=f"{completed} of {total} stages complete")

    for index, label in enumerate(LIVE_ANALYSIS_STAGES):
        icon_col, label_col, state_col = st.columns([1, 6, 3])
        if index < completed:
            icon, state_label = "✅", "Completed"
        elif index == completed and completed < total:
            icon = "⚠️" if failed or limited else "🔵"
            state_label = "Needs attention" if failed or limited else "In progress"
        else:
            icon, state_label = "⚪", "Pending"
        icon_col.write(icon)
        active = index == completed and completed < total
        label_col.write(f"**{label}**" if active else label)
        state_col.caption(state_label)
