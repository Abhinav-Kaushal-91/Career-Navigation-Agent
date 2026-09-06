"""Human approval presentation helpers."""

from collections.abc import Callable

import streamlit as st

from ai_career_navigator.orchestration import PlanReviewAction
from ai_career_navigator.ui.components.cards import render_card


def render_approval_panel(version: str, limitations: tuple[str, ...]) -> None:
    render_card(
        "Review before approval",
        f"You are reviewing {version}. Approval applies only to this displayed version.",
        items=limitations,
        accent=True,
    )


def render_plan_review_actions(
    *,
    plan_version: int,
    limitations: tuple[str, ...],
    on_action: Callable[[PlanReviewAction], None],
) -> None:
    """Render one primary approval and grouped secondary review actions."""

    render_approval_panel(f"plan version {plan_version}", limitations)
    st.caption(
        "Review the plan before approving it. Approval confirms that this is the plan you want "
        "to use as your current career strategy. It does not guarantee an outcome."
    )
    approve, _ = st.columns([1.6, 3.4])
    with approve:
        if st.button("Approve Plan", type="primary", use_container_width=True):
            on_action(PlanReviewAction.APPROVE_AND_SAVE)

    with st.expander("Revise or reassess"):
        options = (
            ("Edit Profile / Preferences", PlanReviewAction.EDIT_PROFILE_OR_PREFERENCES),
            ("Revise Goal", PlanReviewAction.REVISE_GOAL),
            ("Reassess Market", PlanReviewAction.REASSESS_MARKET),
            ("Reassess Career Analysis", PlanReviewAction.REASSESS_CAREER_ANALYSIS),
        )
        columns = st.columns(2)
        for index, (label, action) in enumerate(options):
            with columns[index % 2]:
                if st.button(label, key=f"review_{action.value}", use_container_width=True):
                    on_action(action)

    draft, reject, cancel, _ = st.columns([1.2, 1.4, 1, 2.4])
    for column, label, action in (
        (draft, "Save as Draft", PlanReviewAction.SAVE_AS_DRAFT),
        (reject, "Reject Recommendation", PlanReviewAction.REJECT_RECOMMENDATION),
        (cancel, "Cancel", PlanReviewAction.CANCEL),
    ):
        with column:
            if st.button(label, key=f"review_{action.value}", use_container_width=True):
                on_action(action)
