"""Visual, decision-focused presentation of real graph outputs."""

import asyncio
from collections import defaultdict

import streamlit as st

from ai_career_navigator.domain import PlanStatus
from ai_career_navigator.orchestration import PlanReviewAction
from ai_career_navigator.ui.components.approval import render_plan_review_actions
from ai_career_navigator.ui.components.charts import (
    build_requirement_frequency_figure,
    build_roadmap_figure,
    build_segmented_bar_figure,
    render_donut,
)
from ai_career_navigator.ui.components.layout import render_page_header
from ai_career_navigator.ui.components.navigation import (
    go_to,
    render_workflow_actions,
    surface_graph_workflow_state,
)
from ai_career_navigator.ui.components.states import render_state
from ai_career_navigator.ui.direction_copy import direction_caption
from ai_career_navigator.ui.view_models import (
    analysis_view_model,
    market_view_model,
    plan_eligibility,
    plan_limitations,
    plan_options,
    plan_view_model,
    product_label,
    selected_plan_milestones,
    user_facing_limitations,
)


def _state() -> dict[str, object] | None:
    value = st.session_state.live_graph_state
    return value if isinstance(value, dict) else None


def _display_value(value: object) -> str:
    """Compatibility wrapper for product-safe enum labels."""

    return product_label(value)


def _analysis_view_available(state: dict[str, object]) -> bool:
    """A retained market snapshot always permits an honest Analysis state."""

    return state.get("market_snapshot") is not None


def _unavailable(view: str, back_view: str) -> None:
    render_page_header(view, f"{view} is not available yet", "Run the live analysis first.")
    render_state(
        "No live result",
        "Career Navigator will not substitute synthetic values for missing live workflow data.",
        tone="warning",
    )
    if st.button(f"Back to {back_view}"):
        go_to(back_view)


def _plot(figure: object) -> None:
    st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})


def _confirmed_strengths(state: dict[str, object]) -> None:
    profile = state.get("confirmed_profile")
    names = tuple(
        dict.fromkeys(
            item.capability
            for item in getattr(profile, "approved_evidence_items", ())
            if item.evidence_type.casefold() not in {"employment", "education", "certification"}
        )
    )
    if names:
        st.markdown("**Your confirmed evidence remains available**")
        st.write(" · ".join(names))
        st.caption("Target alignment remains unassessed until usable role evidence is available.")


def _provisional_evidence_notice(state: dict[str, object]) -> None:
    target_profile = state.get("canonical_target_role_profile")
    if getattr(target_profile, "profile_status", None) == "PROVISIONAL":
        st.info(
            "Provisional target-role evidence — this assessment uses a limited sample of "
            "exact or validated equivalent postings. Candidate readiness describes those "
            "requirements, not every employer; check individual postings before acting."
        )


def render_live_market(
    state_override: dict[str, object] | None = None,
    *,
    evidence_label: str | None = None,
) -> None:
    state = state_override if state_override is not None else _state()
    if state is None or state.get("market_snapshot") is None:
        _unavailable("Market", "Goal")
        return
    view = market_view_model(state)
    provider = state.get("market_provider_summary")
    target_profile = state.get("canonical_target_role_profile")

    render_page_header(
        "Market",
        "Current market intelligence",
        f"Current evidence for {view.target_role} roles in {view.geography}.",
    )
    if evidence_label:
        st.caption(evidence_label)
    st.caption(f"Retrieved {view.search_date} · bounded sources · not a complete market count")
    _provisional_evidence_notice(state)
    if getattr(target_profile, "profile_status", None) == "INSUFFICIENT":
        found = (
            "some postings were retained, but their usable hiring evidence is insufficient"
            if view.validated_postings
            else "no postings passed validation in this bounded search"
        )
        st.warning(
            f"Limited target-role evidence — {found}. There is not enough independent "
            "exact or validated equivalent evidence to build a reliable "
            f"profile for {view.target_role} in {view.geography}."
        )
        st.caption(
            "You can broaden the geography, allow credible title variants, try another target "
            "title, or rerun later when more postings may be available."
        )

    st.subheader("Market dimensions")
    for start in range(0, len(view.dimensions), 3):
        row = view.dimensions[start : start + 3]
        for column, dimension in zip(st.columns(len(row)), row, strict=True):
            with column, st.container(border=True, height=190):
                st.caption(dimension.name)
                st.markdown(f"**{dimension.value}**")
                st.caption(dimension.evidence)

    st.subheader("Exact target and expanded market evidence")
    title_counts = (
        ("Exact target postings", view.exact_target_postings),
        ("Target variants", view.target_variant_postings),
        ("Related-title evidence", view.related_title_postings),
        ("Expanded market evidence", view.expanded_market_postings),
    )
    for column, (label, count) in zip(st.columns(4), title_counts, strict=True):
        column.metric(label, count)
    st.caption(
        "Expanded market evidence is the bounded total across exact targets, variants, and "
        "related titles; it is not an exact-target count or a complete market total."
    )

    role_responsibilities = tuple(getattr(target_profile, "responsibilities", ()))
    if role_responsibilities:
        st.subheader("What the role does")
        st.caption(
            "Responsibilities describe the work itself. They do not become candidate "
            "qualifications or gaps unless a posting separately requires that experience."
        )
        for item in role_responsibilities:
            st.write(f"- {item.display_name}")

    st.subheader("What employers appear to want")
    if view.requirement_themes:
        theme_columns = st.columns(2)
        for index, theme in enumerate(view.requirement_themes):
            with theme_columns[index % 2], st.container(border=True):
                st.markdown(f"**{theme.name}**")
                for requirement in theme.requirements:
                    st.write(f"- {requirement}")
    else:
        st.info("No supported requirement themes were found in the analyzed postings.")

    st.subheader("Requirements observed in the target-role sample")
    coverage_text = (
        f"{view.analyzed_postings / view.validated_postings:.0%} coverage"
        if view.validated_postings
        else "coverage unavailable: no validated postings"
    )
    st.caption(
        f"{view.analyzed_postings} of {view.validated_postings} validated postings were "
        f"successfully analyzed ({coverage_text}). The bars use "
        f"{view.primary_analyzed_postings} exact-target or validated-variant postings; "
        "related titles do not affect target-role frequency."
    )
    if view.extraction_quality_summary:
        st.caption(view.extraction_quality_summary)
    with st.expander("From search results to this requirement sample"):
        for label, count in view.evidence_funnel:
            st.write(f"- {label}: {count if count is not None else 'Not recorded'}")
        for reason, count in view.extraction_failures:
            st.write(f"- Extraction outcome — {reason}: {count}")
        st.caption(
            "Search hits can include duplicates and rejected pages. Extraction attempts are "
            "bounded; unexamined or failed postings are not counted as having no requirements. "
            "Unavailable stage details are shown as not recorded."
        )
    if 0 < view.primary_analyzed_postings < 8:
        st.info(
            "Directional sample — too few target-role postings were analyzed to treat these "
            "frequencies as a broad market conclusion."
        )
    if view.requirements:
        _plot(
            build_requirement_frequency_figure(
                tuple(
                    (item.name, item.frequency, item.occurrences, item.sample_size)
                    for item in view.requirements
                )
            )
        )
        with st.expander("How this sample is calculated"):
            st.write(
                "- The denominator contains successfully analyzed exact-target and "
                "validated-variant postings."
            )
            st.write("- Failed requirement extractions are excluded rather than counted as zero.")
            st.write("- Related-title observations remain secondary market context.")
            st.write(f"- Sample confidence: {view.requirement_sample_confidence}.")
    else:
        st.info("No validated requirement frequencies are available.")

    title_column, employer_column = st.columns(2)
    with title_column, st.container(border=True):
        st.markdown("**Posting title mix**")
        st.caption(f"Title relationship across {view.validated_postings} validated postings.")
        if any(count for _, count in view.title_mix):
            _plot(build_segmented_bar_figure(view.title_mix))
        else:
            st.info("No validated posting-title counts are available.")
        st.info(f"{view.title_consistency} — {view.title_conclusion}")
    with employer_column:
        render_donut(
            "Employer concentration",
            f"Share of {view.known_employers} postings with a known employer.",
            view.top_three_share or 0,
            "Top 3 employers",
            "Other employers",
            sample_size=view.known_employers,
        )
        st.info(f"{view.employer_diversity} — {view.employer_conclusion}")

    st.subheader("Geographic distribution")
    st.caption(view.geography_summary)
    st.caption(
        f"Canada-wide postings: {view.canada_wide_postings} · "
        f"Remote or hybrid postings: {view.remote_or_hybrid_postings}"
    )
    if view.geography_counts:
        st.dataframe(
            [
                {"Province or region": region, "Validated postings": count}
                for region, count in view.geography_counts
            ],
            hide_index=True,
            use_container_width=True,
            column_config={
                "Validated postings": st.column_config.ProgressColumn(
                    min_value=0,
                    max_value=max(view.validated_postings, 1),
                    format="%d",
                )
            },
        )

    st.subheader("Market summary")
    for start in range(0, len(view.market_takeaways), 3):
        row = view.market_takeaways[start : start + 3]
        for column, (label, value) in zip(st.columns(len(row)), row, strict=True):
            with column, st.container(border=True, height=160):
                st.caption(label)
                st.markdown(f"**{value}**")

    st.subheader("What this means for your search")
    st.info(view.what_this_means)

    with st.expander("Employers and related titles"):
        employers, related = st.tabs(["Employers", "Related titles"])
        with employers:
            if view.employer_counts:
                st.dataframe(
                    [
                        {"Employer": employer, "Validated postings": count}
                        for employer, count in view.employer_counts
                    ],
                    hide_index=True,
                    use_container_width=True,
                )
            else:
                st.info("Employer names were not available in the validated postings.")
        with related:
            st.write("**Target-title variants**")
            st.write(", ".join(view.target_variant_titles) or "No variants observed.")
            st.write("**Related titles**")
            st.write(", ".join(view.related_titles) or "No related titles observed.")

    with st.expander("Sources and limitations"):
        if provider and provider.primary_provider == "JSEARCH":
            st.write("Job discovery and description details: JSearch")
            st.caption(
                f"{provider.primary_search_count} search requests · "
                f"{provider.enrichment_attempt_count} detail requests"
            )
        elif provider:
            st.write(
                f"Structured discovery: {product_label(provider.primary_provider)} · "
                f"Parallel web discovery: {product_label(provider.enrichment_provider)}"
            )
            st.caption(
                f"{provider.adzuna_validated_count} Adzuna-validated · "
                f"{provider.you_validated_count} You.com-validated · "
                f"{provider.cross_source_match_count} cross-source matches"
            )
        for limitation in view.limitations:
            st.write(f"- {limitation}")
        if not view.limitations:
            st.caption("No material source limitation was recorded for this bounded slice.")

    render_workflow_actions(
        back_label="Back to Goal",
        back_view="Goal",
        primary_label="Continue to Analysis",
        on_primary=lambda: go_to("Analysis"),
    )


def render_live_analysis(
    state_override: dict[str, object] | None = None,
    *,
    evidence_label: str | None = None,
) -> None:
    state = state_override if state_override is not None else _state()
    if state is None or state.get("market_snapshot") is None:
        _unavailable("Analysis", "Market")
        return
    role = state.get("role_assessment")
    if role is None:
        snapshot = state["market_snapshot"]
        analyzed = getattr(state.get("requirement_summary"), "analyzed_posting_count", 0)
        render_page_header(
            "Analysis",
            f"More evidence is needed for {snapshot.target_role}",
            "The current market slice cannot support a candidate comparison yet.",
        )
        metrics = st.columns(3)
        metrics[0].metric("Validated postings", snapshot.validated_posting_count)
        metrics[1].metric("Analyzed postings", analyzed)
        metrics[2].metric("Distinct employers", snapshot.distinct_employer_count)
        st.warning(
            "Sparse availability is not a candidate rejection. The comparison is withheld "
            "because requirement evidence is insufficient."
        )
        _confirmed_strengths(state)
        st.caption(
            "Try broadening the geography, enabling credible title variants, choosing another "
            "target title, or rerunning later."
        )
        actions = st.columns(2)
        if actions[0].button("Back to Market", width="stretch"):
            go_to("Market")
        if actions[1].button("Review Goal", width="stretch"):
            go_to("Goal")
        return
    if state.get("career_assessment_synthesis") is None:
        render_page_header(
            "Analysis",
            f"More evidence is needed for {role.target_role}",
            "The career-level assessment could not be completed safely.",
        )
        st.warning(
            "Your market evidence is preserved, but Career Navigator cannot present a career "
            "interpretation until the synthesis step completes."
        )
        if st.button("Back to Market"):
            go_to("Market")
        return

    view = analysis_view_model(state)
    render_page_header(
        "Analysis",
        f"How your experience compares with {view.target_role}",
        "A career-level assessment grounded in your confirmed evidence and the target market.",
    )
    if evidence_label:
        st.badge(evidence_label, color="orange")

    _provisional_evidence_notice(state)
    assessment_cards = st.columns(3)
    for column, label, value in (
        (assessment_cards[0], "Target role", view.target_role),
        (assessment_cards[1], "Candidate accessibility", view.accessibility),
        (assessment_cards[2], "Assessment confidence", view.confidence),
    ):
        with column, st.container(border=True):
            st.caption(label)
            st.markdown(f"**{value}**")
    st.info(view.assessment_reason)

    metrics = st.columns(4)
    metrics[0].metric("Directly aligned", view.direct_count)
    metrics[1].metric("Transferable strengths", view.transferable_count)
    metrics[2].metric("Partial matches", view.partial_count)
    metrics[3].metric("Material career gaps", view.material_gap_count)

    with st.container(border=True):
        st.markdown("**Evidence match mix**")
        st.caption(
            f"{view.total_requirements} primary-scope comparisons. This shows the evidence mix, "
            "not a readiness score."
        )
        if view.total_requirements:
            _plot(build_segmented_bar_figure(view.coverage, axis_label="Comparisons"))
        else:
            st.info("No primary-scope requirement comparisons are available.")

    st.subheader("What you've demonstrated")
    if view.strongest_matches:
        match_columns = st.columns(min(4, len(view.strongest_matches)))
        for index, item in enumerate(view.strongest_matches):
            with match_columns[index % len(match_columns)], st.container(border=True):
                st.markdown(f"**{item.capability}**")
        with st.expander("Evidence supporting your demonstrated strengths"):
            seen = set()
            for item in view.strongest_matches:
                for detail in item.evidence_details:
                    if detail not in seen:
                        st.write(f"- {detail}")
                        seen.add(detail)
    else:
        st.info("No relevant demonstrated strengths were identified in the approved evidence.")

    st.subheader("How it helps with this target")
    if view.target_alignments:
        for item in view.target_alignments:
            with st.container(border=True):
                source, arrow, target = st.columns([1, 0.18, 1])
                source.caption("What you have demonstrated")
                source.markdown(f"**{item.experience}**")
                arrow.markdown("→")
                target.caption("Target requirement")
                target.markdown(f"**{item.target_requirement}**")
                st.badge(item.alignment, color="blue")
                if item.alignment == "Partially aligned":
                    have, missing = st.columns(2)
                    have.markdown("**What you have**")
                    have.write(item.what_you_have)
                    missing.markdown("**What is still missing**")
                    missing.write(item.still_missing)
                else:
                    st.write(item.what_you_have)
    else:
        st.caption("No grounded target alignments were identified.")

    st.subheader("What you still need to demonstrate")
    if view.grouped_gaps:
        for item in view.grouped_gaps:
            with st.container(border=True):
                heading, severity, importance = st.columns([2.2, 0.9, 1.2])
                heading.markdown(f"**{item.gap}**")
                severity.caption("Severity")
                severity.badge(item.severity, color="orange")
                importance.caption("Market importance")
                importance.markdown(f"**{item.market_importance}**")
                burden = (
                    f"{item.underlying_requirement_count} underlying requirement(s) · "
                    f"{item.severe_requirement_count} high or blocking · "
                    f"{item.mandatory_requirement_count} mandatory · "
                    f"{item.preferred_requirement_count} preferred"
                )
                st.caption(burden)
                st.caption("Affected dimensions: " + ", ".join(item.affected_dimensions))
                with st.expander("Underlying target requirements"):
                    for requirement in item.underlying_requirements:
                        st.write(f"- {requirement}")
                have, missing, close = st.columns(3)
                have.markdown("**What you already have**")
                have.write(item.what_you_have)
                missing.markdown("**What is still missing**")
                missing.write(item.still_missing)
                close.markdown("**Evidence to build**")
                close.write(item.evidence_to_build)
        st.caption(
            f"{view.material_gap_count} career-level theme(s) summarize the underlying burden. "
            "One grouped theme may contain several severe requirements."
        )
    elif view.total_requirements and not view.unassessed_count:
        st.success("No material career-level gaps were identified in the usable comparison.")
    else:
        st.info("Gap analysis is incomplete because target requirements remain unassessed.")

    st.subheader("Readiness by dimension")
    st.caption("Qualitative labels come from the structured dimensions in the career synthesis.")
    if view.readiness_dimensions:
        with st.container(border=True):
            for item in view.readiness_dimensions:
                label, status = st.columns([1.55, 1])
                label.markdown(f"**{item.dimension}**")
                status.badge(item.assessment, color="orange")
                st.caption(item.basis)
    else:
        st.info(
            "No assessed gap dimensions are available yet."
            if not view.total_requirements or view.unassessed_count
            else "No material gap dimensions were identified in the usable comparison."
        )

    st.subheader("What this means for you")
    st.info(view.what_this_means)
    with st.expander("Assessment limitations"):
        for limitation in view.limitations:
            st.write(f"- {limitation}")
    render_workflow_actions(
        back_label="Back to Market",
        back_view="Market",
        primary_label="Continue to Plan",
        on_primary=lambda: go_to("Plan"),
    )


def _phase_rows(milestones: tuple[object, ...]) -> tuple[tuple[str, int, int], ...]:
    grouped: dict[str, list[object]] = defaultdict(list)
    for milestone in milestones:
        grouped[milestone.phase].append(milestone)
    return tuple(
        (phase, min(item.month_start for item in items), max(item.month_end for item in items))
        for phase, items in grouped.items()
    )


def render_live_plan(
    state_override: dict[str, object] | None = None,
    *,
    evidence_label: str | None = None,
) -> None:
    state = state_override if state_override is not None else _state()
    plan = state.get("career_plan") if state else None
    if state and (state.get("same_role_assessment") or state.get("transition_assessment")):
        from ai_career_navigator.ui.pages.same_role import render_same_role_plan

        render_same_role_plan(
            state, read_only=state_override is not None, evidence_label=evidence_label
        )
        return
    if state and direction_caption(state.get("confirmed_goal")):
        st.caption(direction_caption(state.get("confirmed_goal")))
    if state is None or plan is None:
        profile = state.get("canonical_target_role_profile") if state else None
        if getattr(profile, "profile_status", None) == "INSUFFICIENT":
            render_page_header(
                "Plan",
                "A reliable career plan cannot be built yet",
                "The target-role market profile does not have enough independent evidence.",
            )
            st.warning(
                "No candidate accessibility result or approval-ready plan was generated from "
                "the limited target-role evidence."
            )
            _confirmed_strengths(state)
            if st.button("Review Goal"):
                go_to("Goal")
            return
        _unavailable("Plan", "Analysis")
        return
    role = state.get("role_assessment")
    synthesis = state.get("career_assessment_synthesis")
    if synthesis is None:
        render_page_header(
            "Plan",
            "Your plan is not available yet",
            "The synthesized career assessment must be completed before a plan can be shown.",
        )
        st.warning("Your completed profile, goal, and market evidence remain preserved.")
        if st.button("Back to career assessment"):
            go_to("Analysis")
        return
    eligibility = plan_eligibility(plan, role, synthesis)
    view = plan_view_model(plan, role, synthesis)
    render_page_header(
        "Plan",
        "Your career strategy",
        "A practical next step, grounded in your assessment.",
    )
    if evidence_label:
        st.badge(evidence_label, color="orange")
    with st.container(border=True):
        heading, state_badges = st.columns([2, 1], vertical_alignment="center")
        heading.subheader(view.recommended_path)
        heading.caption(f"{view.current_role} → {view.target_role}")
        with state_badges:
            st.badge(f"Plan status: {product_label(plan.plan_status)}", color="gray")
            st.caption(f"{view.accessibility} · Confidence: {view.confidence}")
        if (
            getattr(state.get("canonical_target_role_profile"), "profile_status", None)
            == "PROVISIONAL"
        ):
            st.caption("Provisional target-role evidence — a sampled view, not every employer.")

    if eligibility.missing_actions:
        with st.container(border=True):
            st.subheader("Before this plan is ready")
            for action in eligibility.missing_actions:
                st.write(f"- {action}")
        if view.actions:
            st.markdown("**Specific next steps**")
            for action in view.actions:
                st.write(f"- {action.action}")
        corrective = st.columns(3)
        if corrective[0].button("Review profile", width="stretch"):
            go_to("Profile")
        if corrective[1].button("Review goal", width="stretch"):
            go_to("Goal")
        if corrective[2].button("Re-run analysis", width="stretch"):
            go_to("Analysis")
        return

    options = plan_options(plan)
    selected_id = "primary"
    if options:
        option_ids = {item.option_id for item in options}
        selected_id = st.session_state.get("selected_live_path")
        if selected_id not in option_ids:
            selected_id = next(
                (item.option_id for item in options if item.recommended), options[0].option_id
            )
            st.session_state.selected_live_path = selected_id
        if len(options) > 1:
            st.subheader("Compare supported paths")
            for column, option in zip(st.columns(len(options)), options, strict=True):
                selected = option.option_id == selected_id
                with column, st.container(border=True):
                    st.markdown(f"**{option.title}**")
                    st.caption(option.route)
                    st.caption(f"{option.duration} · {option.effort}")
                    if option.recommended:
                        st.badge("Recommended", color="green")
                    if st.button(
                        "Selected ✓" if selected else "Choose this path",
                        key=f"select_live_path_{option.option_id}",
                        disabled=selected,
                        type="primary" if selected else "secondary",
                        width="stretch",
                    ):
                        st.session_state.selected_live_path = option.option_id
                        st.rerun()

    milestones = selected_plan_milestones(plan, selected_id)
    selected_ids = {item.milestone_id for item in milestones}
    selected_actions = tuple(item for item in view.actions if item.milestone_id in selected_ids)
    journey, context = st.columns([1.8, 1], gap="medium")
    with journey:
        st.subheader("Your roadmap")
        st.caption(
            f"{view.timeline_preference} · Ordered steps, not duration estimates."
            if view.untimed
            else view.timeline_preference
        )
        phases = _phase_rows(milestones)
        if not view.untimed and phases:
            with st.container(border=True):
                _plot(build_roadmap_figure(phases))
        if selected_actions:
            for index, action in enumerate(selected_actions, 1):
                with st.container(border=True):
                    st.caption(f"STEP {index:02d} · {action.career_gap}")
                    st.markdown(f"**{action.action}**")
                    if action.completion_condition:
                        st.caption(f"Done when: {action.completion_condition}")
        else:
            st.info("No additional build action was recorded for this path.")
    with context:
        with st.container(border=True):
            st.subheader("Your direction")
            for index, (stage, role_name) in enumerate(view.route):
                st.caption(stage)
                st.markdown(f"**{role_name}**")
                if index < len(view.route) - 1:
                    st.caption("↓")
        if view.strengths:
            with st.container(border=True):
                st.subheader("Build on")
                for strength in view.strengths:
                    st.write(f"- {strength.title}")
    limitations = plan_limitations(state)
    with st.expander("Plan details"):
        st.markdown("**Why this path**")
        st.write(view.why_this_path)
        for option in options:
            st.markdown(f"**{option.title}**")
            st.write(option.trade_off)
        st.markdown("**Action details**")
        for action in selected_actions:
            st.markdown(f"**{action.career_gap}**")
            st.write(action.why)
            st.caption(f"Outcome: {action.evidence}")
        for title, values in (
            ("Risks", user_facing_limitations(tuple(plan.risks))),
            ("Assumptions", user_facing_limitations(tuple(plan.assumptions))),
            ("Limitations", limitations),
        ):
            if values:
                st.markdown(f"**{title}**")
                for value in dict.fromkeys(values):
                    st.write(f"- {value}")

    st.caption("Approval applies to this displayed version and is session-only in V1.")
    workflow_status = product_label(state.get("workflow_status", ""))
    if plan.plan_status is PlanStatus.APPROVED or workflow_status in {
        "Completed",
        "Completed with limitations",
    }:
        st.success("This plan version is approved.")
    elif eligibility.can_approve:

        def submit(action: PlanReviewAction) -> None:
            if state_override is not None:
                st.session_state.selected_plan_review_action = action.value
                st.session_state.plan_review_confirmation = True
                st.rerun()
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

        if state_override is not None and st.session_state.plan_review_confirmation:
            st.success("The selected action was recorded for this demo session.")
        else:
            render_plan_review_actions(
                plan_version=plan.plan_version,
                limitations=limitations,
                on_action=submit,
                compact=True,
            )
    if st.button("Back to career assessment"):
        go_to("Analysis")
