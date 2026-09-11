"""One decision-focused screen for employer expectations and candidate evidence."""

import streamlit as st

from ai_career_navigator.domain import ConfidenceLevel, MatchType
from ai_career_navigator.market.overview import overview_requirements, source_overview
from ai_career_navigator.ui.components.navigation import go_to
from ai_career_navigator.ui.view_models import analysis_view_model, product_label


def competency_status(match):
    """Short presentation labels; do not convert missing evidence into inability."""
    if (
        match is None
        or match.evidence_status in {"UNKNOWN", "OPERATION_FAILED"}
        or match.clarification_needed
        or match.confidence in {ConfidenceLevel.LOW, ConfidenceLevel.INSUFFICIENT}
    ):
        return "Unknown"
    if match.match_type is MatchType.DIRECT_MATCH:
        return "Yes"
    if match.match_type is MatchType.TRANSFERABLE_MATCH:
        return "Transferable"
    if match.match_type is MatchType.PARTIAL_MATCH:
        return "Partial"
    if match.match_type is MatchType.NO_CONFIRMED_MATCH and match.evidence_status in {
        "CONFIRMED_UNMET",
        "CONTRADICTED",
    }:
        return "No"
    return "Unknown"


def competency_rows(requirements, comparisons):
    """One visible row per canonical competency; retain scope without evidence prose."""

    def scope(item):
        if item.role_importance and item.requirement_kind.value == "PREREQUISITE":
            return "Eligibility"
        if item.role_importance:
            return {
                "CORE": "Core",
                "SUPPORTING": "Supporting",
                "ADDITIONAL": "Additional advantage",
                "SPECIALIST": "Employer-specific",
            }[item.role_importance]
        if not item.exact_support_count and not item.variant_support_count:
            return "Related role"
        if item.requirement_kind.value == "ROLE_RESPONSIBILITY":
            return "Role duty"
        if item.requirement_kind.value == "PREFERENCE":
            return "Preferred"
        if item.employer_specific:
            return "Employer-specific"
        if item.requirement_kind.value == "PREREQUISITE":
            return "Eligibility"
        return "Baseline"

    priority = {
        "Core": 0,
        "Supporting": 2,
        "Additional advantage": 3,
        "Baseline": 0,
        "Eligibility": 1,
        "Preferred": 2,
        "Role duty": 3,
        "Employer-specific": 4,
        "Related role": 5,
    }
    return [
        {
            "No.": index,
            "Competency": (
                comparisons[identifier].matched_alternative
                if item.relationship == "ANY_OF"
                and identifier in comparisons
                and comparisons[identifier].matched_alternative
                and competency_status(comparisons[identifier]) in {"Yes", "Transferable"}
                else item.display_name
            ),
            "Context": scope(item),
            "You": competency_status(comparisons.get(identifier))
            if scope(item) != "Related role"
            else "Context",
        }
        for index, (identifier, item) in enumerate(
            sorted(
                (
                    (key, item)
                    for key, item in requirements.items()
                    if not item.role_importance
                    or (
                        item.role_importance != "SPECIALIST"
                        and item.requirement_kind.value != "ROLE_RESPONSIBILITY"
                    )
                ),
                key=lambda pair: priority[scope(pair[1])],
            ),
            1,
        )
    ]


def assessment_next_step(synthesis, rows):
    """One action from the existing verdict; no new model call or readiness inference."""
    if synthesis is None or synthesis.accessibility.value == "INSUFFICIENT_CANDIDATE_EVIDENCE":
        return (
            "Resolve the outstanding evidence or processing checks in Run details, then reassess."
        )
    if any(row["You"] == "Unknown" and row["Context"] != "Additional advantage" for row in rows):
        return "Confirm unknown items or retry incomplete comparisons, then review your Plan."
    return {
        "APPLY_NOW": "Use your Plan to prepare applications aligned with your confirmed skills.",
        "APPLY_SELECTIVELY": "Prioritize matching openings; verify employer-specific conditions.",
        "NEAR_TERM_TARGET": "Use your Plan to address the key gaps before targeting this role.",
        "ASPIRATIONAL": "Review the development steps and supported alternatives in your Plan.",
        "POOR_FIT": "Review the confirmed barriers and consider revising your target.",
    }.get(
        synthesis.accessibility.value, "Review the remaining checks before choosing your next step."
    )


def render_assessment(state_override=None, *, evidence_label=None) -> None:
    state = (
        state_override if state_override is not None else st.session_state.get("live_graph_state")
    )
    st.caption("CAREER ASSESSMENT")
    st.title("Your career assessment")
    if evidence_label:
        st.badge(evidence_label, color="orange")
    if state and (state.get("same_role_assessment") or state.get("transition_assessment")):
        from ai_career_navigator.ui.pages.same_role import render_same_role_analysis

        render_same_role_analysis(state)
        return
    if not state or state.get("market_snapshot") is None:
        st.info(
            "Run a live analysis from your confirmed goal to see employer expectations "
            "and your fit."
        )
        if st.button("Review goal", key="assessment_empty_goal"):
            go_to("Goal")
        return

    snapshot = state["market_snapshot"]
    role = state.get("role_assessment")
    synthesis = state.get("career_assessment_synthesis")
    canonical = state.get("canonical_target_role_profile")
    processing_issue = getattr(canonical, "extraction_processing_status", "COMPLETE") != "COMPLETE"
    overview = state.get("employer_overview") or source_overview(canonical)
    requirements = overview_requirements(canonical)
    comparisons = {
        item.requirement_id: item for item in getattr(role, "requirement_comparisons", ())
    }
    view = analysis_view_model(state) if role is not None and synthesis is not None else None
    st.caption(f"{snapshot.target_role} · {snapshot.geography}")
    if getattr(canonical, "construction_method", None) == "FIVE_POSTING_BATCH":
        sample_caption = (
            f"{len(canonical.selected_posting_ids)} job descriptions selected"
            if processing_issue
            else f"Combined view of {len(canonical.selected_posting_ids)} job descriptions"
        )
        st.caption(f"{sample_caption} · A searched sample, not the whole market.")
    else:
        st.caption(
            f"{snapshot.validated_posting_count} retained postings · "
            "A searched sample, not the whole market."
        )

    with st.container(border=True):
        heading, status = st.columns([2, 1], vertical_alignment="center")
        if view:
            heading.subheader(view.accessibility)
            confidence = f"Confidence: {view.confidence}"
            if processing_issue:
                confidence += " · Extraction needs review"
            elif getattr(canonical, "profile_status", None) in {"PROVISIONAL", "INSUFFICIENT"}:
                confidence += " · Limited role sample"
            status.caption(confidence)
            # Keep the full rationale in diagnostics; never cut a sentence mid-word.
            reason = view.assessment_reason.split(". ", 1)[0]
            if len(reason) <= 360:
                st.write(reason.rstrip(".") + ".")
        else:
            st.warning("Overall fit not established yet.")
            if processing_issue:
                st.caption("Employer-requirement processing incomplete—not a candidate skill gap.")
            elif getattr(canonical, "profile_status", None) in {"PROVISIONAL", "INSUFFICIENT"}:
                st.caption("Limited role sample")
        if not snapshot.validated_posting_count:
            st.caption("No postings passed validation.")
        if processing_issue:
            st.info(
                "Some model output could not be validated. Valid expectations are retained; "
                "unresolved core expectations prevent an overall fit verdict. "
                "See Run details before retrying from your goal."
            )

    rows = competency_rows(requirements, comparisons)
    duties = list(
        dict.fromkeys(item.display_name for item in getattr(canonical, "responsibilities", ()))
    )
    if duties:
        with st.container(border=True):
            st.subheader("What this role involves")
            for duty in duties[:4]:
                st.markdown(f"- {duty}")
    with st.container(border=True):
        st.subheader("Competency match")
        st.caption("Unknown = unconfirmed. Employer-specific asks are not universal.")
        if rows:
            st.table(rows, border="horizontal", hide_index=True)
        else:
            st.info("No usable employer requirements yet.")
            strengths = list(
                dict.fromkeys(
                    item.capability
                    for item in getattr(
                        state.get("confirmed_profile"), "approved_evidence_items", ()
                    )
                )
            )
            if strengths:
                st.caption("Confirmed strengths: " + " · ".join(strengths))
    gaps, questions = st.columns(2, gap="medium")
    with gaps:
        if view and view.grouped_gaps:
            with st.container(border=True):
                st.subheader("Key gaps")
                for index, gap in enumerate(view.grouped_gaps, 1):
                    st.markdown(f"**{index}. {gap.gap}**")
                    st.caption(gap.severity)
    with questions:
        unknown = [
            row["Competency"]
            for row in rows
            if row["You"] == "Unknown"
            and row["Context"] in {"Core", "Supporting", "Eligibility", "Baseline"}
        ]
        if unknown:
            with st.container(border=True):
                st.subheader("Questions to resolve")
                st.caption("Unconfirmed information—not a confirmed skill gap.")
                for name in unknown:
                    st.markdown(f"- {name}")
    with st.container(border=True):
        st.subheader("Next step")
        st.write(assessment_next_step(synthesis, rows))

    # One optional diagnostic area. No evidence paragraphs or repeated summaries
    # in the decision surface; original audit objects stay intact.
    with st.expander("Run details"):
        if view:
            st.write(view.assessment_reason)
        summary = state.get("requirement_summary")
        if canonical is None:
            st.caption(
                f"{snapshot.validated_posting_count} retained postings · "
                f"{getattr(summary, 'analyzed_posting_count', 0)} analyzed. "
                "Searched sample, not the whole market."
            )
        st.caption(
            f"Exact: {snapshot.exact_title_count}; variants: {snapshot.target_variant_count}; "
            f"related: {snapshot.related_title_count}. Related roles do not define the baseline."
        )
        notes = list(
            dict.fromkeys(
                [
                    *getattr(synthesis, "limitations", ()),
                    *overview.limitations,
                    *state.get("limitations", ()),
                    *getattr(canonical, "limitations", ()),
                    *getattr(canonical, "coverage_limitations", ()),
                    *getattr(summary, "limitations", ()),
                    *(
                        item.clarification_needed
                        for item in comparisons.values()
                        if item.clarification_needed
                    ),
                ]
            )
        )
        for note in notes:
            st.text(note)
        audits = state.get("posting_requirement_audits", ())
        if audits:
            st.table(
                [
                    {
                        "Posting": audit.title,
                        "Employer": audit.employer or "Unspecified",
                        "Location": audit.location or "Unconfirmed",
                        "Scope": product_label(audit.title_classification),
                    }
                    for audit in audits
                ]
            )
            st.caption("Posting leads: verify current availability and employer conditions.")
            st.caption(
                f"{sum(len(audit.items) for audit in audits)} extracted statements retained "
                "in the audit; not all are hiring requirements."
            )
            st.json([audit.model_dump(mode="json") for audit in audits], expanded=False)
        for search in state.get("market_search_passes", ()):
            st.text(search.query)

    back, forward = st.columns(2)
    if back.button("Review goal", key="assessment_goal", width="stretch"):
        go_to("Goal")
    if forward.button(
        "Continue to Plan",
        key="assessment_plan",
        type="primary",
        width="stretch",
        disabled=not (state.get("career_plan") is not None and synthesis is not None),
    ):
        go_to("Plan")


def render() -> None:
    if st.session_state.get("profile_input_mode") == "demo":
        from ai_career_navigator.ui.demo_data import (
            CANDIDATE_PROFILE,
            CAREER_PLAN,
            DEMO_CAREER_SYNTHESIS,
            DEMO_LABEL,
            DEMO_REQUIREMENT_SUMMARY,
            MARKET_SNAPSHOT,
            ROLE_ASSESSMENT,
        )

        render_assessment(
            {
                "market_snapshot": MARKET_SNAPSHOT,
                "role_assessment": ROLE_ASSESSMENT,
                "requirement_summary": DEMO_REQUIREMENT_SUMMARY,
                "career_assessment_synthesis": DEMO_CAREER_SYNTHESIS,
                "confirmed_profile": CANDIDATE_PROFILE,
                "career_plan": CAREER_PLAN,
            },
            evidence_label=DEMO_LABEL,
        )
    else:
        render_assessment()
