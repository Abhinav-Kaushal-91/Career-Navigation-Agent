"""Concise same-role Analysis and Plan, backed by one validated assessment."""

import asyncio
import re

import streamlit as st

from ai_career_navigator.domain import PlanStatus
from ai_career_navigator.ui.components.approval import render_plan_review_actions
from ai_career_navigator.ui.components.navigation import go_to, surface_graph_workflow_state
from ai_career_navigator.ui.direction_copy import direction_caption


def label(value):
    return str(value).replace("_", " ").capitalize()


def is_leadership(assessment):
    return assessment.rule_version.startswith("leadership-")


def assessment_heading(assessment):
    if (
        is_leadership(assessment)
        and getattr(assessment, "current_readiness", None) == "UNCONFIRMED"
        and assessment.accessibility == "NEAR_TERM_TARGET"
    ):
        return "A credible leadership direction"
    return label(assessment.accessibility)


def leadership_rows(assessment):
    """Present existing evidence states; keep non-target records intact in Run details."""
    return [
        {
            "Competency": review_text(c.name, assessment),
            "Your position": (
                "Unconfirmed" if c.evidence_state == "UNKNOWN"
                else "Needs development" if c.evidence_state == "CONFIRMED_SHORTFALL"
                else label(c.status)
            ),
        }
        for c in assessment.competencies
        if c.applicability == "TARGET"
    ]


def main_competencies(assessment):
    if is_leadership(assessment):
        return [c for c in assessment.competencies if c.applicability == "TARGET"]
    return [
        c for c in assessment.competencies
        if c.status != "NOT_RELEVANT" and (
            c.context == "COMMON" or getattr(c, "expectation", None) == "PREREQUISITE"
            or getattr(c, "remaining_need", None) in {"LEARN", "BUILD_EXPERIENCE"}
        )
    ]


def comparison_rows(assessment):
    if is_leadership(assessment):
        return leadership_rows(assessment)
    return [
        {"Competency": review_text(c.name, assessment), "Your position": (
            "Unconfirmed" if c.status == "NOT_ESTABLISHED" else label(c.status)
        )}
        for c in main_competencies(assessment)
    ]


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
    leadership = is_leadership(assessment)
    goal = state["confirmed_goal"]
    st.caption(f"{goal.target_role} · {goal.target_location}")
    if direction_caption(goal):
        st.caption(direction_caption(goal))
    sample_size = len(assessment.posting_sources)
    st.caption(
        f"Based on {sample_size} reviewed job description{'s' if sample_size != 1 else ''}; "
        "not a complete market survey."
    )
    if sample_size == 1:
        st.caption("Limited role sample: this comparison applies to the reviewed role only.")
    with st.container(border=True):
        needs_review = bool(assessment.processing_issues) or assessment.accessibility is None
        st.subheader("Assessment needs review" if needs_review else assessment_heading(assessment))
        # Keep the readiness conclusion up front; the full explanation stays in the audit.
        conclusion = assessment.rationale
        if "-concise-" not in assessment.rule_version:
            conclusion = re.split(r"(?<=[.!?])\s+", conclusion, maxsplit=1)[0]
        if needs_review:
            st.write(
                "Output validation needs review; this is not a candidate skill gap. "
                "Available comparisons are shown below. See Run details for the failed checks."
            )
        else:
            st.write(review_text(conclusion, assessment))
            st.caption(f"Assessment confidence: {label(assessment.confidence)}")
    render_role_overview(assessment)
    strengths = getattr(assessment, "demonstrated_strengths", [])
    if strengths:
        st.subheader("Strengths you bring")
        for strength in strengths:
            name = review_text(strength.name, assessment)
            st.write(f"- **{name}:** {review_text(strength.why_it_helps, assessment)}")
    elif any(c.status == "DEMONSTRATED" for c in main_competencies(assessment)):
        st.subheader("Strengths you bring")
        for c in main_competencies(assessment):
            if c.status == "DEMONSTRATED":
                st.write(f"- {review_text(c.name, assessment)}")
    st.subheader("How you compare")
    st.caption("Unconfirmed means we need more information—not that you lack the experience.")
    rows = comparison_rows(assessment)
    if rows:
        st.table(rows)
    else:
        st.info("No core competency comparisons are available yet.")
    if len(main_competencies(assessment)) < len(assessment.competencies):
        st.caption("Additional and employer-specific expectations remain in Run details.")
    development = [
        c for c in assessment.competencies
        if getattr(c, "development_focus", None)
        and getattr(c, "remaining_need", None) != "CLARIFY"
        and (not leadership or (
            c.applicability == "TARGET" and c.evidence_state == "CONFIRMED_SHORTFALL"
        ))
    ]
    if development:
        st.subheader("What to develop")
        for item in development:
            st.write(review_text(f"**{item.name}** — {item.development_focus}", assessment))
    questions = assessment.questions or [
        getattr(c, "development_focus", None) or f"What experience can you confirm for {c.name}?"
        for c in main_competencies(assessment)
        if getattr(c, "remaining_need", None) == "CLARIFY"
    ]
    if questions:
        st.subheader("Questions before deciding")
        for n, question in enumerate(dict.fromkeys(questions), 1):
            st.write(f"{n}. {review_text(question, assessment)}")
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
    st.title("Your leadership plan" if is_leadership(assessment) else "Your career strategy")
    if evidence_label:
        st.badge(evidence_label, color="orange")
    if not plan:
        st.info("No plan was generated. Review the assessment and outstanding checks.")
        return
    st.caption(f"{plan.current_role} → {plan.target_role}")
    if direction_caption(state.get("confirmed_goal")):
        st.caption(direction_caption(state.get("confirmed_goal")))
    st.subheader(assessment_heading(assessment))
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
