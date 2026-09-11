"""Concise same-role Analysis and Plan, backed by one validated assessment."""

import asyncio
import re

import streamlit as st

from ai_career_navigator.domain import PlanStatus
from ai_career_navigator.ui.components.approval import render_plan_review_actions
from ai_career_navigator.ui.components.navigation import go_to, surface_graph_workflow_state


def label(value):
    return str(value).replace("_", " ").capitalize()


def review_text(value, assessment):
    """Hide source notation in presentation only; never mutate audited output."""
    aliases = set(assessment.posting_sources) | set(assessment.source_lines)
    aliases.update(getattr(assessment, "candidate_sources", {}))
    for competency in assessment.competencies:
        aliases.update(competency.candidate_refs)
    for strength in getattr(assessment, "demonstrated_strengths", []):
        aliases.update(strength.candidate_refs)
    # Restrict removal to supplied aliases, not legitimate skills such as L2 support.
    if aliases:
        pattern = r"\b(?:" + "|".join(re.escape(a) for a in sorted(aliases, key=len, reverse=True))
        # Remove whole citation-only brackets first, preserving ordinary parentheses.
        token = pattern + r")\b"
        citation = rf"{token}(?:(?:\s*[,;]\s*|\s+and\s+){token})*"
        value = re.sub(rf"[\[(]\s*{citation}\s*[\])]", "", value)
        replacements = {
            alias: f"the reviewed {source.get('title') or 'job'} role"
            for alias, source in assessment.posting_sources.items()
        }
        candidate_aliases = aliases - set(assessment.posting_sources) - set(assessment.source_lines)
        replacements.update({alias: "your recorded experience" for alias in candidate_aliases})
        value = re.sub(token, lambda match: replacements.get(match.group(), ""), value)
    value = re.sub(r"\(\s*[,;\s]*\)|\[\s*[,;\s]*\]", "", value)
    value = re.sub(r"[ \t]+", " ", value)
    return re.sub(r"\s+([.,;:])", r"\1", value).strip()


def render_role_overview(assessment):
    """Summarize already-classified expectations, not individual posting stories."""
    st.subheader("What this role involves")
    if "-concise-" in assessment.rule_version:
        st.write(review_text(assessment.role_picture, assessment))
        return
    for context, heading in (
        ("COMMON", "Shared expectations"),
        ("SPECIALIST", "Specialist skills — depend on the direction"),
        ("OPTIONAL", "Additional advantages"),
    ):
        names = list(
            dict.fromkeys(
                review_text(item.name, assessment)
                for item in assessment.competencies
                if item.context == context
            )
        )
        if names:
            st.markdown(f"**{heading}**")
            st.write(" · ".join(names))
    if not assessment.competencies:
        st.info("Role expectations are not available yet.")


def render_same_role_analysis(state):
    assessment = state.get("transition_assessment") or state["same_role_assessment"]
    goal = state["confirmed_goal"]
    st.caption(f"{goal.target_role} · {goal.target_location}")
    st.caption(
        f"Based on {len(assessment.posting_sources)} reviewed job descriptions; "
        "not a complete market survey."
    )
    with st.container(border=True):
        st.subheader(label(assessment.accessibility))
        # Keep the readiness conclusion up front; the full explanation stays in the audit.
        conclusion = assessment.rationale
        if "-concise-" not in assessment.rule_version:
            conclusion = re.split(r"(?<=[.!?])\s+", conclusion, maxsplit=1)[0]
        st.write(review_text(conclusion, assessment))
        st.caption(f"Assessment confidence: {label(assessment.confidence)}")
    if assessment.processing_issues:
        st.warning(
            "Some output could not be verified. "
            "This is a processing issue, not a candidate skill gap."
        )
    render_role_overview(assessment)
    strengths = getattr(assessment, "demonstrated_strengths", [])
    if strengths:
        st.subheader("Strengths you bring to this transition")
        for strength in strengths:
            st.write(f"- {review_text(strength.name, assessment)}")
    st.subheader("Competency match")
    st.caption(
        "Not established means unconfirmed—not inability. Specialist asks are not universal."
    )
    st.table(
        [
            {
                "Competency": review_text(c.name, assessment),
                "Context": label(c.context),
                "You": label(c.status),
                **({"Next need": label(c.remaining_need)} if hasattr(c, "remaining_need") else {}),
            }
            for c in assessment.competencies
        ]
    )
    development = [c for c in assessment.competencies if getattr(c, "development_focus", None)]
    if development:
        st.subheader("What needs building or clarifying")
        for item in development:
            st.write(review_text(f"**{item.name}** — {item.development_focus}", assessment))
    if assessment.questions:
        st.subheader("Questions to resolve")
        for question in assessment.questions:
            st.write(f"- {review_text(question, assessment)}")
    with st.expander("Run details"):
        st.caption(f"Rules: {assessment.rule_version}")
        st.write(assessment.rationale)
        st.write(assessment.role_picture)
        for opportunity in assessment.opportunities:
            source = assessment.posting_sources.get(opportunity.posting_ref, {})
            st.markdown(f"**{source.get('employer') or 'Employer not supplied'}**")
            st.caption(f"{source.get('title', '')} · {label(opportunity.fit)}")
            st.write(opportunity.reason)
        for item in assessment.competencies:
            st.markdown(f"**{item.name}**")
            st.write(item.reason)
            if getattr(item, "transfer_explanation", None):
                st.write(item.transfer_explanation)
            for ref in item.source_refs:
                st.caption(f"{ref}: {assessment.source_lines.get(ref, 'Unavailable')}")
        for limitation in [*assessment.limitations, *assessment.processing_issues]:
            st.write(f"- {limitation}")
    if state.get("career_plan") and st.button("Continue to Plan", type="primary"):
        go_to("Plan")


def render_same_role_plan(state, *, read_only=False, evidence_label=None):
    assessment = state.get("transition_assessment") or state["same_role_assessment"]
    plan = state.get("career_plan")
    st.title("Your career strategy")
    if evidence_label:
        st.badge(evidence_label, color="orange")
    if not plan:
        st.info("No plan was generated. Review the assessment and outstanding checks.")
        return
    st.caption(f"{plan.current_role} → {plan.target_role}")
    st.subheader(label(assessment.accessibility))
    st.caption(f"Plan confidence: {label(assessment.confidence)}")
    st.caption(review_text(plan.timing_basis, assessment))
    for milestone in plan.milestones:
        with st.container(border=True):
            st.caption(milestone.phase)
            st.write(review_text(milestone.action, assessment))
            st.caption(f"Done when: {review_text(milestone.measurable_outcome, assessment)}")
    with st.expander("Plan details"):
        st.write(assessment.rationale)
        for milestone in plan.milestones:
            st.caption(f"{milestone.phase} builds on: {milestone.basis}")
            if (
                review_text(milestone.action, assessment) != milestone.action
                or review_text(milestone.measurable_outcome, assessment)
                != milestone.measurable_outcome
            ):
                st.write(milestone.action)
                st.caption(milestone.measurable_outcome)
        for limitation in assessment.limitations:
            st.write(f"- {limitation}")
    st.caption("Approval applies to this exact plan version. Saving is session-only in V1.")
    if plan.plan_status == PlanStatus.APPROVED:
        st.success("This plan version is approved.")
    elif read_only:
        st.caption("Saved-run preview: review actions are disabled.")
    else:

        def submit(action):
            runtime = st.session_state.live_workflow_runtime
            result = asyncio.run(
                runtime.controller.submit_plan_action(
                    thread_id=st.session_state.live_thread_id,
                    plan_id=plan.plan_id,
                    plan_version=plan.plan_version,
                    action=action,
                )
            )
            st.session_state.live_graph_state = result.state
            st.session_state.live_graph_interrupts = result.interrupts
            surface_graph_workflow_state(result.state)
            st.rerun()

        render_plan_review_actions(
            plan_version=plan.plan_version,
            limitations=tuple(review_text(item, assessment) for item in assessment.limitations),
            on_action=submit,
            compact=True,
        )
    if st.button("Back to career assessment"):
        go_to("Analysis")
