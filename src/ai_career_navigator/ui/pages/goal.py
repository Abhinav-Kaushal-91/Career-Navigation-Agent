"""Deterministic career-goal selection, review, confirmation, and live launch."""

import asyncio
from collections.abc import Callable
from time import perf_counter
from uuid import uuid4

import streamlit as st
from pydantic import ValidationError

from ai_career_navigator.domain import CandidateProfile, CareerGoal, GeographyScope, GoalType
from ai_career_navigator.goal import (
    GOAL_INTENT_CONFIGS,
    GoalDraft,
    GoalValidationError,
    confirm_career_goal,
    format_goal_review,
    goal_intent_config,
    validate_goal_draft,
)
from ai_career_navigator.orchestration.failure_diagnostics import (
    record_live_failure,
    safe_failure_code,
)
from ai_career_navigator.ui.components.badges import render_status_badge
from ai_career_navigator.ui.components.cards import render_card
from ai_career_navigator.ui.components.layout import render_page_header
from ai_career_navigator.ui.components.navigation import (
    go_to,
    invalidate_workflow_after_goal_change,
    surface_graph_workflow_state,
)
from ai_career_navigator.ui.components.progress import (
    completed_stage_count,
    render_live_analysis_progress,
)
from ai_career_navigator.ui.components.states import render_state
from ai_career_navigator.ui.demo_data import CAREER_GOAL, DEMO_LABEL
from ai_career_navigator.ui.live_workflow import (
    build_live_workflow_runtime,
    load_live_settings,
)

TIMELINE_OPTIONS = (
    "No fixed timeline",
    "6 months",
    "12 months",
    "18 months",
    "24 months",
    "36 months",
)
WORK_MODE_OPTIONS = ("On-site", "Hybrid", "Remote", "Flexible / No preference")
INDUSTRY_OPTIONS = (
    "Financial Services",
    "Insurance",
    "Technology",
    "Healthcare",
    "Public Sector",
    "Consulting",
    "No preference",
)
GEOGRAPHY_SCOPE_LABELS = {
    GeographyScope.STRICT_CITY: "City only",
    GeographyScope.METRO_AREA: "Greater metro area",
    GeographyScope.PROVINCE: "Province-wide",
    GeographyScope.COUNTRY: "Anywhere in Canada",
    GeographyScope.COUNTRY_REMOTE: "Canada-wide remote",
}


def _draft() -> GoalDraft | None:
    raw = st.session_state.goal_draft
    return GoalDraft.model_validate(raw) if raw is not None else None


def _save_draft(draft: GoalDraft) -> None:
    st.session_state.goal_draft = draft.model_dump(mode="json")
    st.session_state.selected_goal_type = draft.goal_type.value
    st.session_state.goal_confirmed = False
    st.session_state.confirmed_goal = None


def _split_entries(value: str) -> list[str]:
    return [
        item.strip().removeprefix("- ")
        for line in value.splitlines()
        for item in line.split(",")
        if item.strip()
    ]


def _validation_message(error: ValidationError) -> str:
    first = error.errors()[0]
    location = " ".join(str(item).replace("_", " ") for item in first["loc"])
    message = str(first["msg"]).removeprefix("Value error, ")
    return f"{location.title()}: {message}" if location else message


def _select_goal_type(goal_type: GoalType) -> None:
    previous = _draft()
    config = goal_intent_config(goal_type)
    draft = GoalDraft(
        goal_type=goal_type,
        target_role=previous.target_role if previous and config.target_label else None,
        target_seniority=previous.target_seniority if previous and config.target_label else None,
        target_timeline_months=(
            previous.target_timeline_months if previous and config.show_timeline else None
        ),
        target_location=previous.target_location if previous else None,
        target_industries=previous.target_industries if previous else [],
        preferred_work_modes=previous.preferred_work_modes if previous else [],
        geography_scopes=previous.geography_scopes if previous else [],
        bridge_role_willingness=(
            previous.bridge_role_willingness
            if previous and config.show_bridge_willingness
            else None
        ),
        search_expansion_permission=(
            previous.search_expansion_permission
            if previous and config.show_search_expansion
            else False
        ),
        exclusions=previous.exclusions if previous else [],
    )
    _save_draft(draft)
    st.session_state.goal_review_ready = False
    st.rerun()


def _render_goal_selection(*, demo: bool) -> None:
    render_page_header(
        "Goal",
        "What would you like to understand?",
        "Choose a direction. You’ll only see details that are useful for that question.",
    )
    if demo:
        render_status_badge(DEMO_LABEL)
    goal_types = tuple(GOAL_INTENT_CONFIGS)
    for start in range(0, len(goal_types), 3):
        columns = st.columns(3)
        for column, goal_type in zip(columns, goal_types[start : start + 3], strict=True):
            config = goal_intent_config(goal_type)
            with column:
                with st.container(border=True, key=f"goal_direction_{goal_type.value.lower()}"):
                    with st.container(height=145, border=False):
                        st.markdown(f"**{config.label}**")
                        st.caption(config.description)
                    if st.button(
                        "Choose this direction",
                        key=f"choose_goal_{goal_type.value.lower()}",
                        use_container_width=True,
                    ):
                        _select_goal_type(goal_type)
        st.write("")
    if st.button("Back to Profile", type="tertiary"):
        go_to("Profile")


def _timeline_label(months: int | None) -> str:
    label = f"{months} months" if months else "No fixed timeline"
    return label if label in TIMELINE_OPTIONS else "No fixed timeline"


def _bridge_label(value: bool | None) -> str:
    if value is True:
        return "Yes"
    if value is False:
        return "No"
    return "Unsure"


def _render_goal_details(draft: GoalDraft, *, demo: bool) -> None:
    config = goal_intent_config(draft.goal_type)
    render_page_header("Goal Details", config.label, config.description)
    if demo:
        render_status_badge(DEMO_LABEL)

    extra_industries = tuple(
        item for item in draft.target_industries if item not in INDUSTRY_OPTIONS
    )
    industry_options = (*INDUSTRY_OPTIONS, *extra_industries)
    with st.form("goal_details_form"):
        target_role = draft.target_role
        target_seniority = draft.target_seniority
        if config.target_label:
            target_column, seniority_column = st.columns(2)
            with target_column:
                target_role = st.text_input(
                    config.target_label,
                    value=draft.target_role or "",
                    placeholder="Enter a role title or leadership level",
                )
            with seniority_column:
                target_seniority = st.text_input(
                    "Target seniority (optional)", value=draft.target_seniority or ""
                )

        timeline_months = draft.target_timeline_months
        if config.show_timeline:
            timeline = st.selectbox(
                "Desired timeline",
                TIMELINE_OPTIONS,
                index=TIMELINE_OPTIONS.index(_timeline_label(draft.target_timeline_months)),
                help="This is your preference. Timeline realism is assessed later.",
            )
            timeline_months = None if timeline == TIMELINE_OPTIONS[0] else int(timeline.split()[0])

        st.subheader("Preferences")
        location_column, work_mode_column = st.columns(2)
        with location_column:
            location = st.text_input(
                "Target location (optional)",
                value=draft.target_location or "",
                placeholder="Toronto, Canada; Remote; Open to relocation",
            )
        with work_mode_column:
            work_modes = st.multiselect(
                "Preferred work modes",
                WORK_MODE_OPTIONS,
                default=draft.preferred_work_modes,
            )

        scope_options = [
            GeographyScope.STRICT_CITY,
            GeographyScope.METRO_AREA,
            GeographyScope.PROVINCE,
            GeographyScope.COUNTRY,
        ]
        if "Remote" in work_modes:
            scope_options.append(GeographyScope.COUNTRY_REMOTE)
        default_scope = (
            GeographyScope.COUNTRY
            if location.strip().casefold() == "canada"
            else GeographyScope.STRICT_CITY
        )
        selected_scope_defaults = [
            scope for scope in (draft.geography_scopes or [default_scope]) if scope in scope_options
        ]
        geography_scopes = st.multiselect(
            "How far may the location search extend?",
            scope_options,
            default=selected_scope_defaults,
            format_func=lambda scope: GEOGRAPHY_SCOPE_LABELS[scope],
            help=(
                "Only selected areas will be searched. Canada-wide remote is available "
                "only when Remote is an accepted work mode."
            ),
        )

        industries = st.multiselect(
            "Industry preferences (optional)",
            industry_options,
            default=draft.target_industries,
        )
        custom_industries = st.text_input(
            "Other industries (optional)", help="Separate multiple industries with commas."
        )

        bridge_willingness = draft.bridge_role_willingness
        if config.show_bridge_willingness:
            bridge_choice = st.radio(
                "Would you consider an intermediate role if it supports this direction?",
                ("Yes", "No", "Unsure"),
                index=("Yes", "No", "Unsure").index(_bridge_label(draft.bridge_role_willingness)),
                horizontal=True,
            )
            bridge_willingness = {"Yes": True, "No": False, "Unsure": None}[bridge_choice]

        search_expansion = False
        if config.show_search_expansion:
            expansion_choice = st.radio(
                "If there are few exact matches, should Career Navigator also look at closely "
                "related roles?",
                ("Yes", "No"),
                index=0 if draft.search_expansion_permission else 1,
                horizontal=True,
            )
            search_expansion = expansion_choice == "Yes"

        exclusions = st.text_area(
            "Constraints or exclusions (optional)",
            value="\n".join(draft.exclusions),
            help="Examples: No relocation, no contract roles, avoid heavy travel. One per line.",
        )
        submitted = st.form_submit_button("Review Goal", type="primary")

    if submitted:
        try:
            updated = GoalDraft(
                goal_type=draft.goal_type,
                target_role=target_role,
                target_seniority=target_seniority,
                target_timeline_months=timeline_months,
                target_location=location,
                target_industries=[*industries, *_split_entries(custom_industries)],
                preferred_work_modes=work_modes,
                geography_scopes=geography_scopes,
                bridge_role_willingness=bridge_willingness,
                search_expansion_permission=search_expansion,
                exclusions=_split_entries(exclusions),
            )
            validate_goal_draft(updated)
            _save_draft(updated)
            st.session_state.goal_review_ready = True
            st.rerun()
        except ValidationError as error:
            st.error(_validation_message(error))
        except GoalValidationError as error:
            st.error(str(error))

    back, change, _ = st.columns([1.3, 1.4, 2.5])
    with back:
        if st.button("Back to Profile", use_container_width=True):
            go_to("Profile")
    with change:
        if st.button("Change direction", type="tertiary", use_container_width=True):
            _change_goal_direction()


def _render_review_cards(draft: GoalDraft) -> None:
    rows = format_goal_review(draft)
    columns = st.columns(2)
    for index, (label, value) in enumerate(rows):
        with columns[index % 2]:
            render_card(label, value)


def _edit_goal() -> None:
    invalidate_workflow_after_goal_change()
    st.session_state.goal_review_ready = False
    st.session_state.goal_confirmed = False
    st.session_state.confirmed_goal = None
    st.rerun()


def _change_goal_direction() -> None:
    invalidate_workflow_after_goal_change()
    st.session_state.selected_goal_type = None
    st.session_state.goal_review_ready = False
    st.session_state.goal_confirmed = False
    st.session_state.confirmed_goal = None
    st.rerun()


def _safe_live_failure_message(category: str | None) -> str:
    messages = {
        "MARKET_TIMEOUT": (
            "The job-search request timed out. Your profile and goal are unchanged. "
            "Wait briefly, then retry. Model-based analysis has not started."
        ),
        "MARKET_RATE_LIMIT": (
            "The job-search provider returned a rate or quota limit. Check your RapidAPI "
            "usage before retrying. Model-based analysis has not started."
        ),
        "MARKET_RESPONSE_INVALID": (
            "The job-search response could not be read in the expected format. "
            "Your profile and goal are unchanged; no replacement data was used."
        ),
        "SCHEMA_VALIDATION_ERROR": (
            "The application could not validate data at this step. "
            "This is a processing issue, not a candidate skill gap."
        ),
        "MODEL_TIMEOUT": "The model request timed out. Review the run details before retrying.",
        "MODEL_PROVIDER_ERROR": "The model provider could not complete the request.",
        "ROLE_DISCOVERY_REQUIRED": (
            "Choose a named target role before running the current V1 market analysis."
        ),
        "AUTHENTICATION_ERROR": (
            "The market provider rejected its credentials. Check provider configuration and retry."
        ),
        "CONFIGURATION_ERROR": (
            "The live market provider is not configured correctly. Your profile and goal remain "
            "available. For JSearch, add RAPIDAPI_KEY to your local environment file."
        ),
        "MARKET_PROCESSING_ERROR": (
            "The retrieved postings could not be processed safely. No synthetic result was used."
        ),
        "MARKET_PROCESSING_FAILED": (
            "Employer requirements could not be validated from the retrieved postings."
        ),
        "MARKETTRANSPORTERROR": (
            "The live market sources could not be reached. Check the connection and retry; "
            "Model-based requirement extraction has not started."
        ),
        "MARKET_TRANSPORT_ERROR": (
            "The live market sources could not be reached. Check the connection and retry; "
            "Model-based requirement extraction has not started."
        ),
        "INTERRUPTED_RUN": (
            "The previous analysis run was interrupted before it finished. Your confirmed "
            "profile and goal are unchanged."
        ),
    }
    return messages.get(
        safe_failure_code(category),
        "The live analysis stopped safely before producing a market result. Retry when ready.",
    )


def _market_result_available(state: dict[str, object]) -> bool:
    """A retrieved snapshot remains reviewable when later analysis is incomplete."""

    return state.get("market_snapshot") is not None


def _render_goal_review(draft: GoalDraft, *, demo: bool) -> None:
    render_page_header(
        "Goal Review",
        "Review your career goal",
        "This records what you want assessed. It does not judge feasibility or start a search.",
    )
    if demo:
        render_status_badge(DEMO_LABEL)
    _render_review_cards(draft)
    edit, change, _, confirm = st.columns([1.3, 1.4, 1.6, 1.5])
    with edit:
        if st.button("Edit Goal", use_container_width=True):
            _edit_goal()
    with change:
        if st.button("Change Direction", type="tertiary", use_container_width=True):
            _change_goal_direction()
    with confirm:
        if st.button("Confirm Goal", type="primary", use_container_width=True):
            try:
                st.session_state.confirmed_goal = confirm_career_goal(draft).model_dump(mode="json")
                st.session_state.goal_confirmed = True
                st.rerun()
            except GoalValidationError as error:
                st.error(str(error))


def _confirmed_goal() -> CareerGoal:
    return CareerGoal.model_validate(st.session_state.confirmed_goal)


def _start_live_workflow(goal: CareerGoal, *, on_progress: Callable[[str], None]) -> bool:
    started = perf_counter()
    st.session_state.live_failure_diagnostic = None

    def record_failure(category, state=None, *, stage=None):
        state = state or {}
        st.session_state.live_failure_diagnostic = record_live_failure(
            category,
            stage=stage or state.get("current_stage", "WORKFLOW_EXECUTION"),
            elapsed_seconds=perf_counter() - started,
            run_id=state.get("run_id"),
            market_result_preserved=_market_result_available(state),
            last_checkpoint_stage=state.get("current_stage"),
        )

    if not goal.target_role:
        st.session_state.live_workflow_error = "ROLE_DISCOVERY_REQUIRED"
        return False
    # Each explicit run/retry gets fresh provider configuration and a new graph
    # checkpoint. Profile and goal state remain intact, while stale failed-run
    # state cannot leak into the next attempt.
    try:
        profile = CandidateProfile.model_validate(st.session_state.confirmed_profile)
        runtime = build_live_workflow_runtime(load_live_settings())
    except Exception as error:
        st.session_state.live_workflow_error = type(error).__name__
        record_failure(type(error).__name__, stage="INITIALIZATION")
        return False
    st.session_state.live_workflow_runtime = runtime
    thread_id = f"live-{uuid4()}"
    st.session_state.live_thread_id = thread_id
    st.session_state.live_graph_state = None
    st.session_state.live_graph_interrupts = []
    st.session_state.live_workflow_error = None
    try:

        async def execute_workflow():  # type: ignore[no-untyped-def]
            async for node_name in runtime.controller.stream_start(
                thread_id=thread_id,
                confirmed_profile=profile,
                confirmed_goal=goal,
                capability_inference_requested=False,
            ):
                on_progress(node_name)
            return runtime.controller.inspect(thread_id=thread_id)

        result = asyncio.run(execute_workflow())
        st.session_state.live_graph_state = result.state
        st.session_state.live_graph_interrupts = result.interrupts
        surface_graph_workflow_state(result.state)
        if _market_result_available(result.state):
            workflow_status = getattr(
                result.state.get("workflow_status"),
                "value",
                result.state.get("workflow_status"),
            )
            complete = workflow_status != "FAILED"
            if not complete:
                category = result.state.get("last_error") or "MARKET_PROCESSING_FAILED"
                st.session_state.live_workflow_error = str(category)
                record_failure(category, result.state)
            st.session_state.live_analysis_requested = False
            go_to("Market")
        else:
            category = result.state.get("last_error")
            if category is None:
                status = result.state.get("workflow_status")
                category = getattr(status, "value", status)
            st.session_state.live_workflow_error = str(category or "LIVE_ANALYSIS_FAILED")
            record_failure(category, result.state)
            return False
    except Exception as error:  # UI boundary presents only a safe category
        st.session_state.live_workflow_error = type(error).__name__
        # Streaming may fail after retrieval has checkpointed a valid market
        # snapshot. Preserve and surface that evidence instead of claiming that
        # no market result exists.
        try:
            recovered = runtime.controller.inspect(thread_id=thread_id)
            st.session_state.live_graph_state = recovered.state
            st.session_state.live_graph_interrupts = recovered.interrupts
            surface_graph_workflow_state(recovered.state)
        except Exception:
            recovered = None
        record_failure(
            type(error).__name__,
            recovered.state if recovered is not None else None,
            stage="WORKFLOW_EXECUTION",
        )
        if recovered is not None and _market_result_available(recovered.state):
            st.session_state.live_analysis_requested = False
            go_to("Market")
        return False
    return True


def _request_live_analysis() -> None:
    st.session_state.live_workflow_error = None
    st.session_state.live_failure_diagnostic = None
    st.session_state.live_analysis_completed_stages = 0
    st.session_state.live_analysis_requested = True
    st.rerun()


def _render_failure_details() -> None:
    st.caption(f"Error code: {safe_failure_code(st.session_state.live_workflow_error)}")
    diagnostic = st.session_state.get("live_failure_diagnostic")
    if diagnostic:
        with st.expander("Failure details"):
            st.json(diagnostic)
            if diagnostic["record_saved"]:
                st.caption("Sanitized diagnostic saved locally in outputs/failed-runs.")
            else:
                st.caption("Local diagnostic could not be saved; the error code remains available.")


def _render_live_analysis_transition(goal: CareerGoal) -> None:
    render_page_header(
        "Live Analysis",
        "Building your career analysis…",
        "We're combining your confirmed experience with current market evidence.",
    )
    st.caption(
        "This run uses your confirmed profile and goal. No demo result will replace missing "
        "live evidence."
    )
    progress_area = st.empty()

    def update_progress(node_name: str | None = None, *, failed: bool = False) -> None:
        if node_name is not None:
            completed = completed_stage_count(node_name)
            st.session_state.live_analysis_completed_stages = max(
                st.session_state.live_analysis_completed_stages,
                completed,
            )
        with progress_area.container(border=True):
            render_live_analysis_progress(
                st.session_state.live_analysis_completed_stages,
                failed=failed,
            )

    def render_recovery() -> None:
        render_state(
            "Live analysis paused",
            _safe_live_failure_message(st.session_state.live_workflow_error),
            tone="warning",
        )
        _render_failure_details()
        retry, back, _ = st.columns([1.2, 1.4, 2.4])
        with retry:
            if st.button("Retry analysis", type="primary", use_container_width=True):
                _request_live_analysis()
        with back:
            if st.button("Back to goal", use_container_width=True):
                st.rerun()

    update_progress()
    if st.session_state.live_analysis_running:
        st.session_state.live_analysis_running = False
        st.session_state.live_analysis_requested = False
        st.session_state.live_workflow_error = "INTERRUPTED_RUN"
        update_progress(failed=True)
        render_recovery()
        return

    st.session_state.live_analysis_running = True
    try:
        completed = _start_live_workflow(goal, on_progress=update_progress)
    finally:
        st.session_state.live_analysis_running = False

    if completed:
        return

    st.session_state.live_analysis_requested = False
    update_progress(failed=True)
    render_recovery()


def _render_confirmed_goal(*, demo: bool) -> None:
    goal = _confirmed_goal()
    if not demo and st.session_state.live_analysis_requested:
        _render_live_analysis_transition(goal)
        return
    draft = GoalDraft(
        goal_type=goal.goal_type,
        target_role=goal.target_role,
        target_seniority=goal.target_seniority,
        target_timeline_months=goal.target_timeline_months,
        target_location=goal.target_location,
        target_industries=goal.target_industries,
        preferred_work_modes=goal.preferred_work_modes,
        geography_scopes=goal.geography_scopes,
        bridge_role_willingness=goal.bridge_role_willingness,
        search_expansion_permission=goal.search_expansion_permission,
        exclusions=goal.exclusions,
    )
    render_page_header(
        "Goal Confirmed",
        "Your career goal is ready",
        "Your confirmed profile and goal are ready for live market and career analysis.",
    )
    render_status_badge("APPROVED", prefix="Goal")
    if demo:
        render_status_badge(DEMO_LABEL)
    _render_review_cards(draft)
    role_discovery_required = not goal.target_role
    config = goal_intent_config(goal.goal_type)
    target_can_be_added = config.target_label is not None
    if role_discovery_required:
        next_action = (
            "Add a role title to search and analyze the live market."
            if target_can_be_added
            else "Change to a named-target direction to run live market analysis."
        )
        render_state(
            "Target role needed for live analysis",
            (
                "This goal is valid, but open-ended role discovery is not implemented in the "
                f"current V1 workflow. {next_action}"
            ),
            tone="warning",
        )
    elif st.session_state.live_workflow_error:
        render_state(
            "Live analysis unavailable",
            "The last run stopped safely. Review your settings and retry when ready.",
            tone="warning",
        )
        st.caption(_safe_live_failure_message(st.session_state.live_workflow_error))
        _render_failure_details()
    back, edit, change, forward = st.columns([1.2, 1.3, 1.3, 1.7])
    with back:
        if st.button("Back to Profile", use_container_width=True):
            go_to("Profile")
    with edit:
        edit_label = (
            "Add Target Role" if role_discovery_required and target_can_be_added else "Edit Goal"
        )
        if st.button(
            edit_label,
            use_container_width=True,
            type=("primary" if role_discovery_required and target_can_be_added else "secondary"),
        ):
            _edit_goal()
    with change:
        if st.button("Change Direction", type="tertiary", use_container_width=True):
            _change_goal_direction()
    with forward:
        if role_discovery_required:
            st.caption("Market analysis becomes available after a target role is added.")
        elif demo:
            if st.button("Continue Demo", type="primary", use_container_width=True):
                go_to("Market")
        elif st.button("Run Live Analysis", type="primary", use_container_width=True):
            _request_live_analysis()


def _initialize_demo_goal() -> None:
    if st.session_state.goal_draft is not None:
        return
    demo_draft = GoalDraft(
        goal_type=CAREER_GOAL.goal_type,
        target_role=CAREER_GOAL.target_role,
        target_seniority=CAREER_GOAL.target_seniority,
        target_timeline_months=CAREER_GOAL.target_timeline_months,
        target_location=CAREER_GOAL.target_location,
        target_industries=CAREER_GOAL.target_industries,
        preferred_work_modes=CAREER_GOAL.preferred_work_modes,
        geography_scopes=CAREER_GOAL.geography_scopes,
        bridge_role_willingness=CAREER_GOAL.bridge_role_willingness,
        search_expansion_permission=CAREER_GOAL.search_expansion_permission,
        exclusions=CAREER_GOAL.exclusions,
    )
    _save_draft(demo_draft)


def render() -> None:
    demo = st.session_state.profile_input_mode == "demo"
    if demo:
        _initialize_demo_goal()
    if st.session_state.goal_confirmed:
        _render_confirmed_goal(demo=demo)
        return
    draft = _draft()
    if st.session_state.selected_goal_type is None or draft is None:
        _render_goal_selection(demo=demo)
    elif st.session_state.goal_review_ready:
        _render_goal_review(draft, demo=demo)
    else:
        _render_goal_details(draft, demo=demo)
