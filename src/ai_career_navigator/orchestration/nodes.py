"""Thin graph nodes that delegate business behavior to existing services."""

from time import perf_counter
from uuid import UUID, uuid4

from langgraph.runtime import Runtime
from langgraph.types import interrupt

from ai_career_navigator.career import (
    BridgeAnalysisResult,
    BridgeAnalysisStatus,
    CandidateComparisonStatus,
    GapAnalysisStatus,
    PlanGenerationStatus,
    TimelineAnalysisStatus,
)
from ai_career_navigator.domain import (
    ApprovalStatus,
    CandidateProfile,
    ConfidenceLevel,
    EvidenceConfirmationStatus,
    EvidenceItem,
    PlanStatus,
)
from ai_career_navigator.market import (
    MarketProviderSummary,
    PostingGeographyStatus,
    PostingTitleMatch,
    RequirementRunStatus,
    RoleProfileStatus,
)
from ai_career_navigator.market.errors import (
    MarketAuthenticationError,
    MarketConfigurationError,
    MarketIntelligenceError,
)
from ai_career_navigator.profile import InferenceRunStatus, add_inferred_evidence

from .approval import (
    REVISION_PLAN_ACTIONS,
    PlanReviewAction,
    PlanReviewRequest,
    action_record,
)
from .audit import persist_run_audit
from .context import WorkflowRuntimeContext, retrieval_limits
from .invalidation import revision_invalidation
from .state import (
    CapabilityWorkflowStatus,
    CareerGraphState,
    HumanAction,
    MarketProcessingWorkflowStatus,
    MarketSearchWorkflowStatus,
    WorkflowStage,
    WorkflowStatus,
)

WORKFLOW_VERSION = "career-synthesis-v1"


def _unique(existing: list[str], additions: list[str]) -> list[str]:
    return list(dict.fromkeys([*existing, *additions]))


def _completed(state: CareerGraphState, stage: WorkflowStage) -> list[WorkflowStage]:
    return list(dict.fromkeys([*state.get("completed_stages", []), stage]))


def _log_node(
    runtime: Runtime[WorkflowRuntimeContext],
    *,
    run_id: UUID,
    node: str,
    started: float,
    status: str,
    limitation_count: int,
    error_category: str | None = None,
    route: str | None = None,
) -> None:
    runtime.context.logger.info(
        "workflow_node_completed run_id=%s node=%s status=%s limitation_count=%d "
        "error_category=%s route=%s elapsed_ms=%d",
        run_id,
        node,
        status,
        limitation_count,
        error_category,
        route,
        (perf_counter() - started) * 1000,
    )


def initialize_run(
    state: CareerGraphState, runtime: Runtime[WorkflowRuntimeContext]
) -> dict[str, object]:
    started = perf_counter()
    timestamp = runtime.context.clock()
    run_id = state.get("run_id", uuid4())
    update: dict[str, object] = {
        "run_id": run_id,
        "workflow_version": state.get("workflow_version", WORKFLOW_VERSION),
        "started_at": state.get("started_at", timestamp),
        "updated_at": timestamp,
        "completed_at": state.get("completed_at"),
        "current_stage": WorkflowStage.INITIALIZE,
        "workflow_status": WorkflowStatus.RUNNING,
        "confirmed_profile": state.get("confirmed_profile"),
        "confirmed_goal": state.get("confirmed_goal"),
        "capability_inference_requested": state.get("capability_inference_requested", True),
        "capability_inference_status": state.get(
            "capability_inference_status", CapabilityWorkflowStatus.NOT_STARTED
        ),
        "inferred_evidence": state.get("inferred_evidence", []),
        "inference_review_completed": state.get("inference_review_completed", False),
        "market_search_status": state.get(
            "market_search_status", MarketSearchWorkflowStatus.NOT_STARTED
        ),
        "market_snapshot": state.get("market_snapshot"),
        "market_provider_summary": state.get("market_provider_summary"),
        "market_source_ids": state.get("market_source_ids", []),
        "market_posting_audits": state.get("market_posting_audits", []),
        "market_search_passes": state.get("market_search_passes", []),
        "market_processing_status": state.get(
            "market_processing_status", MarketProcessingWorkflowStatus.NOT_STARTED
        ),
        "requirement_summary": state.get("requirement_summary"),
        "canonical_target_role_profile": state.get("canonical_target_role_profile"),
        "initial_canonical_target_role_profile": state.get("initial_canonical_target_role_profile"),
        "posting_requirement_audits": state.get("posting_requirement_audits", []),
        "target_variant_audits": state.get("target_variant_audits", []),
        "target_variant_expansion_attempted": state.get(
            "target_variant_expansion_attempted", False
        ),
        "requirement_comparisons": state.get("requirement_comparisons", []),
        "candidate_comparison_status": state.get("candidate_comparison_status"),
        "comparison_limitations": state.get("comparison_limitations", []),
        "role_assessment": state.get("role_assessment"),
        "career_assessment_synthesis": state.get("career_assessment_synthesis"),
        "gap_analysis_status": state.get("gap_analysis_status"),
        "candidate_accessibility": state.get("candidate_accessibility"),
        "gap_limitations": state.get("gap_limitations", []),
        "bridge_assessments": state.get("bridge_assessments", []),
        "bridge_outcome": state.get("bridge_outcome"),
        "bridge_analysis_status": state.get("bridge_analysis_status"),
        "bridge_would_help": state.get("bridge_would_help", False),
        "timeline_assessment": state.get("timeline_assessment"),
        "timeline_analysis_status": state.get("timeline_analysis_status"),
        "career_path_limitations": state.get("career_path_limitations", []),
        "career_plan": state.get("career_plan"),
        "career_plan_status": state.get("career_plan_status"),
        "plan_limitations": state.get("plan_limitations", []),
        "plan_review_request": state.get("plan_review_request"),
        "workflow_action_records": state.get("workflow_action_records", []),
        "limitations": state.get("limitations", []),
        "warnings": state.get("warnings", []),
        "retry_counts": state.get("retry_counts", {}),
        "last_error": None,
        "human_action_required": None,
        "completed_stages": state.get("completed_stages", []),
        "degraded_mode": state.get("degraded_mode", False),
        "audit_artifact_path": state.get("audit_artifact_path"),
    }
    _log_node(
        runtime,
        run_id=run_id,
        node="initialize_run",
        started=started,
        status=WorkflowStatus.RUNNING,
        limitation_count=len(update["limitations"]),  # type: ignore[arg-type]
        route="profile_ready",
    )
    return update


def profile_ready(
    state: CareerGraphState, runtime: Runtime[WorkflowRuntimeContext]
) -> dict[str, object]:
    started = perf_counter()
    run_id = state["run_id"]
    profile = state.get("confirmed_profile")
    if profile is None:
        update: dict[str, object] = {
            "current_stage": WorkflowStage.PROFILE_READY,
            "workflow_status": WorkflowStatus.READY_FOR_PROFILE,
            "last_error": None,
            "updated_at": runtime.context.clock(),
        }
    elif profile.approval_status is not ApprovalStatus.APPROVED:
        update = {
            "current_stage": WorkflowStage.PROFILE_READY,
            "workflow_status": WorkflowStatus.FAILED,
            "last_error": "INVALID_CONFIRMED_PROFILE",
            "updated_at": runtime.context.clock(),
        }
    else:
        update = {
            "current_stage": WorkflowStage.PROFILE_READY,
            "workflow_status": WorkflowStatus.RUNNING,
            "completed_stages": _completed(state, WorkflowStage.PROFILE_READY),
            "updated_at": runtime.context.clock(),
        }
    _log_node(
        runtime,
        run_id=run_id,
        node="profile_ready",
        started=started,
        status=str(update["workflow_status"]),
        limitation_count=len(state.get("limitations", [])),
        error_category=update.get("last_error"),  # type: ignore[arg-type]
        route=(
            "capability_inference" if update["workflow_status"] is WorkflowStatus.RUNNING else "end"
        ),
    )
    return update


def capability_inference(
    state: CareerGraphState, runtime: Runtime[WorkflowRuntimeContext]
) -> dict[str, object]:
    started = perf_counter()
    run_id = state["run_id"]
    profile = state["confirmed_profile"]
    assert profile is not None
    prior_status = state.get("capability_inference_status", CapabilityWorkflowStatus.NOT_STARTED)
    if not state.get("capability_inference_requested", True):
        status = CapabilityWorkflowStatus.NOT_REQUESTED
        inferred: list[EvidenceItem] = []
        updated_profile = profile
        limitations: list[str] = []
    elif prior_status in {
        CapabilityWorkflowStatus.REVIEWED,
        CapabilityWorkflowStatus.COMPLETED,
        CapabilityWorkflowStatus.EMPTY,
        CapabilityWorkflowStatus.FAILED_CONTINUED,
    }:
        status = prior_status
        inferred = state.get("inferred_evidence", [])
        updated_profile = profile
        limitations = []
    else:
        pending = [
            item
            for item in profile.evidence_items
            if item.confirmation_status is EvidenceConfirmationStatus.INFERRED_PENDING
        ]
        if pending:
            status = CapabilityWorkflowStatus.REVIEW_REQUIRED
            inferred = pending
            updated_profile = profile
            limitations = []
        else:
            outcome = runtime.context.capability_inference_service(
                profile, runtime.context.model_gateway
            )
            inferred = list(outcome.inferred_evidence)
            limitations = list(outcome.result.limitations)
            if outcome.status is InferenceRunStatus.FAILED:
                status = CapabilityWorkflowStatus.FAILED_CONTINUED
                updated_profile = profile
                limitations.append(
                    outcome.error_message
                    or "Capability inference was unavailable; confirmed evidence was preserved."
                )
            elif outcome.status is InferenceRunStatus.EMPTY:
                status = CapabilityWorkflowStatus.EMPTY
                updated_profile = profile
            else:
                status = CapabilityWorkflowStatus.REVIEW_REQUIRED
                updated_profile = add_inferred_evidence(profile, tuple(inferred))

    all_limitations = _unique(state.get("limitations", []), limitations)
    update = {
        "current_stage": WorkflowStage.CAPABILITY_INFERENCE,
        "confirmed_profile": updated_profile,
        "capability_inference_status": status,
        "inferred_evidence": inferred,
        "workflow_status": (
            WorkflowStatus.WAITING_FOR_HUMAN
            if status is CapabilityWorkflowStatus.REVIEW_REQUIRED
            else WorkflowStatus.RUNNING
        ),
        "human_action_required": (
            HumanAction.CAPABILITY_INFERENCE_REVIEW
            if status is CapabilityWorkflowStatus.REVIEW_REQUIRED
            else None
        ),
        "limitations": all_limitations,
        "degraded_mode": bool(all_limitations) or state.get("degraded_mode", False),
        "completed_stages": _completed(state, WorkflowStage.CAPABILITY_INFERENCE),
        "updated_at": runtime.context.clock(),
    }
    _log_node(
        runtime,
        run_id=run_id,
        node="capability_inference",
        started=started,
        status=status,
        limitation_count=len(all_limitations),
        route=(
            "capability_inference_review"
            if status is CapabilityWorkflowStatus.REVIEW_REQUIRED
            else "goal_ready"
        ),
    )
    if status is CapabilityWorkflowStatus.REVIEW_REQUIRED:
        runtime.context.logger.info(
            "workflow_human_pause run_id=%s action=%s",
            run_id,
            HumanAction.CAPABILITY_INFERENCE_REVIEW.value,
        )
    return update


def _review_is_valid(original: CandidateProfile, reviewed: CandidateProfile) -> bool:
    if (
        reviewed.profile_id != original.profile_id
        or reviewed.profile_version != original.profile_version
        or reviewed.approval_status is not ApprovalStatus.APPROVED
    ):
        return False
    original_by_id = {item.evidence_id: item for item in original.evidence_items}
    reviewed_by_id = {item.evidence_id: item for item in reviewed.evidence_items}
    if set(original_by_id) != set(reviewed_by_id):
        return False
    for evidence_id, item in original_by_id.items():
        if item.confirmation_status is EvidenceConfirmationStatus.EXPLICIT:
            if reviewed_by_id[evidence_id] != item:
                return False
    return True


def capability_inference_review(
    state: CareerGraphState, runtime: Runtime[WorkflowRuntimeContext]
) -> dict[str, object]:
    """Pause for review; no external call or mutation occurs before the interrupt."""

    response = interrupt(
        {
            "action": HumanAction.CAPABILITY_INFERENCE_REVIEW.value,
            "run_id": str(state["run_id"]),
            "inferred_evidence": [
                item.model_dump(mode="json") for item in state.get("inferred_evidence", [])
            ],
        }
    )
    try:
        reviewed = CandidateProfile.model_validate(response["confirmed_profile"])
        review_completed = response.get("review_completed") is True
    except (KeyError, TypeError, ValueError):
        reviewed = state["confirmed_profile"]
        review_completed = False
    original = state["confirmed_profile"]
    if original is None or reviewed is None or not review_completed:
        return {
            "workflow_status": WorkflowStatus.FAILED,
            "last_error": "INVALID_INFERENCE_REVIEW",
            "human_action_required": None,
        }
    if not _review_is_valid(original, reviewed):
        return {
            "workflow_status": WorkflowStatus.FAILED,
            "last_error": "INFERENCE_REVIEW_MISMATCH",
            "human_action_required": None,
        }
    reviewed_inferences = [
        item
        for item in reviewed.evidence_items
        if item.confirmation_status is not EvidenceConfirmationStatus.EXPLICIT
    ]
    runtime.context.logger.info(
        "workflow_human_resume run_id=%s action=%s",
        state["run_id"],
        HumanAction.CAPABILITY_INFERENCE_REVIEW.value,
    )
    return {
        "current_stage": WorkflowStage.CAPABILITY_INFERENCE_REVIEW,
        "confirmed_profile": reviewed,
        "inferred_evidence": reviewed_inferences,
        "capability_inference_status": CapabilityWorkflowStatus.REVIEWED,
        "inference_review_completed": True,
        "human_action_required": None,
        "workflow_status": WorkflowStatus.RUNNING,
        "completed_stages": _completed(state, WorkflowStage.CAPABILITY_INFERENCE_REVIEW),
        "updated_at": runtime.context.clock(),
    }


def goal_ready(
    state: CareerGraphState, runtime: Runtime[WorkflowRuntimeContext]
) -> dict[str, object]:
    started = perf_counter()
    goal = state.get("confirmed_goal")
    if goal is None:
        status = WorkflowStatus.READY_FOR_GOAL
        last_error = None
        market_status = state.get("market_search_status", MarketSearchWorkflowStatus.NOT_STARTED)
    elif goal.approval_status is not ApprovalStatus.APPROVED:
        status = WorkflowStatus.FAILED
        last_error = "INVALID_CONFIRMED_GOAL"
        market_status = MarketSearchWorkflowStatus.FAILED
    elif not goal.target_role:
        status = WorkflowStatus.ROLE_DISCOVERY_REQUIRED
        last_error = None
        market_status = MarketSearchWorkflowStatus.ROLE_DISCOVERY_REQUIRED
    else:
        status = WorkflowStatus.RUNNING
        last_error = None
        market_status = state.get("market_search_status", MarketSearchWorkflowStatus.NOT_STARTED)
    update = {
        "current_stage": WorkflowStage.GOAL_READY,
        "workflow_status": status,
        "market_search_status": market_status,
        "last_error": last_error,
        "completed_stages": _completed(state, WorkflowStage.GOAL_READY),
        "updated_at": runtime.context.clock(),
    }
    _log_node(
        runtime,
        run_id=state["run_id"],
        node="goal_ready",
        started=started,
        status=status,
        limitation_count=len(state.get("limitations", [])),
        error_category=last_error,
        route="market_retrieval" if status is WorkflowStatus.RUNNING else "end",
    )
    return update


async def market_retrieval(
    state: CareerGraphState, runtime: Runtime[WorkflowRuntimeContext]
) -> dict[str, object]:
    started = perf_counter()
    goal = state["confirmed_goal"]
    assert goal is not None
    retries = dict(state.get("retry_counts", {}))
    try:
        result = await runtime.context.retrieve_market(
            goal,
            limits=retrieval_limits(runtime.context.settings),
            now=runtime.context.clock(),
        )
    except MarketAuthenticationError:
        error_category = "AUTHENTICATION_ERROR"
    except MarketConfigurationError:
        error_category = "CONFIGURATION_ERROR"
    except MarketIntelligenceError as error:
        error_category = type(error).__name__.upper()
        retries["market_retrieval"] = retries.get("market_retrieval", 0) + 1
    else:
        if result.requires_role_discovery:
            return {
                "workflow_status": WorkflowStatus.ROLE_DISCOVERY_REQUIRED,
                "market_search_status": MarketSearchWorkflowStatus.ROLE_DISCOVERY_REQUIRED,
                "updated_at": runtime.context.clock(),
            }
        source_ids = (
            runtime.context.content_store.put_posting_evidence(
                state["run_id"], result.posting_evidence
            )
            if result.posting_evidence
            else runtime.context.content_store.put(state["run_id"], result.source_contents)
        )
        new_limitations = result.snapshot.limitations if result.snapshot else []
        limitations = _unique(state.get("limitations", []), new_limitations)
        limited = bool(new_limitations) or (
            result.snapshot is not None
            and result.snapshot.evidence_confidence
            in {ConfidenceLevel.LOW, ConfidenceLevel.INSUFFICIENT}
        )
        search_status = (
            MarketSearchWorkflowStatus.LIMITED if limited else MarketSearchWorkflowStatus.SUCCEEDED
        )
        update = {
            "current_stage": WorkflowStage.MARKET_RETRIEVAL,
            "market_search_status": search_status,
            "market_snapshot": result.snapshot,
            "market_provider_summary": MarketProviderSummary(
                primary_provider=result.primary_provider,
                enrichment_provider=result.enrichment_provider,
                degraded_discovery=result.degraded_discovery,
                primary_search_count=result.primary_search_count,
                enrichment_attempt_count=result.enrichment_attempt_count,
                enrichment_success_count=result.enrichment_success_count,
                parallel_discovery=result.parallel_discovery,
                you_search_count=result.you_search_count,
                adzuna_raw_result_count=result.adzuna_raw_result_count,
                adzuna_validated_count=result.adzuna_validated_count,
                you_validated_count=result.you_validated_count,
                cross_source_match_count=result.cross_source_match_count,
                source_coverage_confidence=result.source_coverage_confidence,
                source_coverage_reason=result.source_coverage_reason,
                you_raw_result_count=result.you_raw_result_count,
                you_direct_posting_count=result.you_direct_posting_count,
                you_context_result_count=result.you_context_result_count,
                you_rejected_result_count=result.you_rejected_result_count,
                you_fallback_triggered=result.you_fallback_triggered,
            ),
            "market_source_ids": source_ids,
            "market_posting_audits": result.posting_audits,
            "market_search_passes": result.search_passes,
            "limitations": limitations,
            "degraded_mode": limited or state.get("degraded_mode", False),
            "workflow_status": WorkflowStatus.RUNNING,
            "completed_stages": _completed(state, WorkflowStage.MARKET_RETRIEVAL),
            "updated_at": runtime.context.clock(),
        }
        _log_node(
            runtime,
            run_id=state["run_id"],
            node="market_retrieval",
            started=started,
            status=search_status,
            limitation_count=len(limitations),
            route="market_processing",
        )
        return update

    _log_node(
        runtime,
        run_id=state["run_id"],
        node="market_retrieval",
        started=started,
        status=MarketSearchWorkflowStatus.FAILED,
        limitation_count=len(state.get("limitations", [])),
        error_category=error_category,
        route="end",
    )
    return {
        "current_stage": WorkflowStage.MARKET_RETRIEVAL,
        "market_search_status": MarketSearchWorkflowStatus.FAILED,
        "workflow_status": WorkflowStatus.FAILED,
        "retry_counts": retries,
        "last_error": error_category,
        "updated_at": runtime.context.clock(),
    }


def market_processing(
    state: CareerGraphState, runtime: Runtime[WorkflowRuntimeContext]
) -> dict[str, object]:
    started = perf_counter()
    goal = state["confirmed_goal"]
    assert goal is not None and goal.target_role is not None
    processing_inputs = runtime.context.content_store.get_processing_inputs(state["run_id"])
    if state.get("market_source_ids") and not processing_inputs:
        error_category = "TRANSIENT_MARKET_CONTENT_UNAVAILABLE"
        result = None
    else:
        try:
            result = runtime.context.market_processing_service(
                processing_inputs,
                target_role=goal.target_role,
                geography=goal.target_location or "Location not specified",
                target_seniority=goal.target_seniority,
                model_gateway=runtime.context.model_gateway,
                allow_related_titles=goal.search_expansion_permission,
                enable_target_variant_expansion=goal.search_expansion_permission,
                posting_limit=runtime.context.settings.market_analysis_posting_limit,
                now=runtime.context.clock(),
            )
            error_category = None
        except Exception as error:  # graph boundary converts internals to a safe category
            runtime.context.logger.warning(
                "workflow_market_processing_failed run_id=%s category=%s",
                state["run_id"],
                type(error).__name__,
            )
            result = None
            error_category = "MARKET_PROCESSING_ERROR"

    if result is None or result.status is RequirementRunStatus.FAILED:
        error_category = error_category or "MARKET_PROCESSING_FAILED"
        limitations = list(state.get("limitations", []))
        failure_update: dict[str, object] = {}
        if result is not None:
            # The retrieval snapshot and extraction-quality facts are still
            # useful evidence even when no posting passed strict extraction.
            runtime.context.content_store.put_analysis(state["run_id"], result)
            limitations = _unique(limitations, result.summary.limitations)
            failure_update["requirement_summary"] = result.summary
            failure_update["canonical_target_role_profile"] = result.canonical_profile
            failure_update["initial_canonical_target_role_profile"] = (
                result.initial_canonical_profile
            )
            failure_update["posting_requirement_audits"] = result.posting_audits
            failure_update["target_variant_audits"] = result.target_variant_audits
            failure_update["target_variant_expansion_attempted"] = (
                result.target_variant_expansion_attempted
            )
        _log_node(
            runtime,
            run_id=state["run_id"],
            node="market_processing",
            started=started,
            status=MarketProcessingWorkflowStatus.FAILED,
            limitation_count=len(state.get("limitations", [])),
            error_category=error_category,
            route="end",
        )
        return {
            "current_stage": WorkflowStage.MARKET_PROCESSING,
            "market_processing_status": MarketProcessingWorkflowStatus.FAILED,
            "workflow_status": WorkflowStatus.FAILED,
            "last_error": error_category,
            "limitations": limitations,
            "degraded_mode": True,
            "updated_at": runtime.context.clock(),
            **failure_update,
        }

    target_profile_insufficient = bool(
        result.canonical_profile
        and result.canonical_profile.profile_status is RoleProfileStatus.INSUFFICIENT
    )
    limited = (
        result.status in {RequirementRunStatus.PARTIAL, RequirementRunStatus.EMPTY}
        or target_profile_insufficient
    )
    runtime.context.content_store.put_analysis(state["run_id"], result)
    limitations = _unique(state.get("limitations", []), result.summary.limitations)
    snapshot = state.get("market_snapshot")
    if snapshot is not None and result.target_variant_expansion_attempted:
        exact = [
            item
            for item in result.assessments
            if item.geography_status is PostingGeographyStatus.IN_SCOPE
            if item.title_match is PostingTitleMatch.EXACT_TARGET
        ]
        variants = [
            item
            for item in result.assessments
            if item.geography_status is PostingGeographyStatus.IN_SCOPE
            if item.title_match is PostingTitleMatch.TARGET_VARIANT
        ]
        related = [
            item
            for item in result.assessments
            if item.geography_status is PostingGeographyStatus.IN_SCOPE
            if item.title_match is PostingTitleMatch.RELATED_TITLE
        ]
        if len(exact) + len(variants) + len(related) == snapshot.validated_posting_count:
            snapshot = snapshot.model_copy(
                update={
                    "exact_title_count": len(exact),
                    "target_variant_count": len(variants),
                    "related_title_count": len(related),
                    "target_variant_titles": list(
                        dict.fromkeys(item.candidate.title for item in variants)
                    ),
                    "related_titles": list(dict.fromkeys(item.candidate.title for item in related)),
                }
            )
    processing_status = (
        MarketProcessingWorkflowStatus.LIMITED
        if limited
        else MarketProcessingWorkflowStatus.SUCCEEDED
    )
    update = {
        "current_stage": WorkflowStage.MARKET_PROCESSING,
        "market_processing_status": processing_status,
        "requirement_summary": result.summary,
        "market_snapshot": snapshot,
        "canonical_target_role_profile": result.canonical_profile,
        "initial_canonical_target_role_profile": result.initial_canonical_profile,
        "posting_requirement_audits": result.posting_audits,
        "target_variant_audits": result.target_variant_audits,
        "target_variant_expansion_attempted": result.target_variant_expansion_attempted,
        "limitations": limitations,
        "degraded_mode": limited or bool(limitations) or state.get("degraded_mode", False),
        "workflow_status": WorkflowStatus.RUNNING,
        "completed_stages": _completed(state, WorkflowStage.MARKET_PROCESSING),
        "updated_at": runtime.context.clock(),
    }
    _log_node(
        runtime,
        run_id=state["run_id"],
        node="market_processing",
        started=started,
        status=processing_status,
        limitation_count=len(limitations),
        route="market_ready",
    )
    return update


def market_ready(
    state: CareerGraphState, runtime: Runtime[WorkflowRuntimeContext]
) -> dict[str, object]:
    limitations = state.get("limitations", [])
    profile = state.get("canonical_target_role_profile")
    target_profile_insufficient = bool(
        profile and profile.profile_status is RoleProfileStatus.INSUFFICIENT
    )
    workflow_status = (
        WorkflowStatus.INSUFFICIENT_EVIDENCE
        if target_profile_insufficient
        else WorkflowStatus.COMPLETED_WITH_LIMITATIONS
        if state.get("degraded_mode", False) or limitations
        else WorkflowStatus.MARKET_READY
    )
    runtime.context.logger.info(
        "workflow_market_ready run_id=%s status=%s limitation_count=%d",
        state["run_id"],
        workflow_status,
        len(limitations),
    )
    return {
        "current_stage": WorkflowStage.MARKET_READY,
        "workflow_status": workflow_status,
        "completed_stages": _completed(state, WorkflowStage.MARKET_READY),
        "updated_at": runtime.context.clock(),
    }


def candidate_requirement_comparison(
    state: CareerGraphState, runtime: Runtime[WorkflowRuntimeContext]
) -> dict[str, object]:
    """Delegate candidate comparison to the career service and expose typed state."""

    started = perf_counter()
    profile = state.get("confirmed_profile")
    analysis = runtime.context.content_store.get_analysis(state["run_id"])
    if profile is None or analysis is None:
        status = (
            CandidateComparisonStatus.INSUFFICIENT_CANDIDATE_EVIDENCE
            if profile is None
            else CandidateComparisonStatus.INSUFFICIENT_MARKET_REQUIREMENTS
        )
        comparisons = []
        comparison_limitations = [
            "Candidate comparison inputs were not available in the active workflow run."
        ]
    else:
        result = runtime.context.candidate_comparison_service(
            profile, analysis, runtime.context.model_gateway
        )
        status = result.status
        comparisons = result.comparisons
        comparison_limitations = result.limitations

    limitations = _unique(state.get("limitations", []), comparison_limitations)
    limited = status is not CandidateComparisonStatus.SUCCEEDED
    update = {
        "current_stage": WorkflowStage.CANDIDATE_COMPARISON_READY,
        "candidate_comparison_status": status,
        "requirement_comparisons": comparisons,
        "comparison_limitations": comparison_limitations,
        "limitations": limitations,
        "degraded_mode": limited or state.get("degraded_mode", False),
        "workflow_status": (
            WorkflowStatus.COMPLETED_WITH_LIMITATIONS
            if limited or state.get("degraded_mode", False)
            else WorkflowStatus.CANDIDATE_COMPARISON_READY
        ),
        "completed_stages": _completed(state, WorkflowStage.CANDIDATE_REQUIREMENT_COMPARISON)
        + [WorkflowStage.CANDIDATE_COMPARISON_READY],
        "updated_at": runtime.context.clock(),
    }
    _log_node(
        runtime,
        run_id=state["run_id"],
        node="candidate_requirement_comparison",
        started=started,
        status=status,
        limitation_count=len(comparison_limitations),
        route="end",
    )
    return update


def gap_and_accessibility_analysis(
    state: CareerGraphState, runtime: Runtime[WorkflowRuntimeContext]
) -> dict[str, object]:
    """Delegate deterministic gap and accessibility policy to the career service."""

    started = perf_counter()
    profile = state.get("confirmed_profile")
    goal = state.get("confirmed_goal")
    snapshot = state.get("market_snapshot")
    analysis = runtime.context.content_store.get_analysis(state["run_id"])
    if profile is None or goal is None or snapshot is None or analysis is None:
        return {
            "current_stage": WorkflowStage.CANDIDATE_ASSESSMENT_READY,
            "gap_analysis_status": GapAnalysisStatus.INSUFFICIENT,
            "candidate_accessibility": None,
            "gap_limitations": ["Gap-analysis inputs were unavailable in the active run."],
            "workflow_status": WorkflowStatus.COMPLETED_WITH_LIMITATIONS,
            "degraded_mode": True,
            "updated_at": runtime.context.clock(),
        }
    result = runtime.context.gap_analysis_service(
        profile,
        goal,
        snapshot,
        analysis,
        state.get("requirement_comparisons", []),
    )
    limitations = _unique(state.get("limitations", []), result.limitations)
    limited = result.status is not GapAnalysisStatus.SUCCEEDED
    update = {
        "current_stage": WorkflowStage.CANDIDATE_ASSESSMENT_READY,
        "role_assessment": result.role_assessment,
        "gap_analysis_status": result.status,
        "candidate_accessibility": result.role_assessment.candidate_accessibility,
        "gap_limitations": result.limitations,
        "limitations": limitations,
        "degraded_mode": limited or state.get("degraded_mode", False),
        "workflow_status": (
            WorkflowStatus.COMPLETED_WITH_LIMITATIONS
            if limited or state.get("degraded_mode", False)
            else WorkflowStatus.CANDIDATE_ASSESSMENT_READY
        ),
        "completed_stages": _completed(state, WorkflowStage.GAP_AND_ACCESSIBILITY_ANALYSIS)
        + [WorkflowStage.CANDIDATE_ASSESSMENT_READY],
        "updated_at": runtime.context.clock(),
    }
    _log_node(
        runtime,
        run_id=state["run_id"],
        node="gap_and_accessibility_analysis",
        started=started,
        status=result.status,
        limitation_count=len(result.limitations),
        route="end",
    )
    return update


def bridge_role_assessment(
    state: CareerGraphState, runtime: Runtime[WorkflowRuntimeContext]
) -> dict[str, object]:
    """Evaluate bridge roles from already-observed related-title evidence."""

    profile = state.get("confirmed_profile")
    goal = state.get("confirmed_goal")
    role = state.get("role_assessment")
    snapshot = state.get("market_snapshot")
    analysis = runtime.context.content_store.get_analysis(state["run_id"])
    if not all((profile, goal, role, snapshot, analysis)):
        return {
            "bridge_analysis_status": BridgeAnalysisStatus.INSUFFICIENT,
            "career_path_limitations": ["Bridge-analysis inputs were unavailable."],
            "workflow_status": WorkflowStatus.COMPLETED_WITH_LIMITATIONS,
            "degraded_mode": True,
        }
    result = runtime.context.bridge_analysis_service(
        profile, goal, role, analysis, snapshot.related_titles
    )
    limitations = _unique(state.get("limitations", []), result.limitations)
    return {
        "current_stage": WorkflowStage.BRIDGE_ROLE_ASSESSMENT,
        "bridge_assessments": result.assessments,
        "bridge_outcome": result.outcome,
        "bridge_analysis_status": result.status,
        "bridge_would_help": result.bridge_would_help,
        "career_path_limitations": result.limitations,
        "limitations": limitations,
        "degraded_mode": bool(result.limitations) or state.get("degraded_mode", False),
        "workflow_status": WorkflowStatus.RUNNING,
        "completed_stages": _completed(state, WorkflowStage.BRIDGE_ROLE_ASSESSMENT),
        "updated_at": runtime.context.clock(),
    }


def career_assessment_synthesis(
    state: CareerGraphState, runtime: Runtime[WorkflowRuntimeContext]
) -> dict[str, object]:
    """Create the validated career-level interpretation used by Analysis and Plan."""

    started = perf_counter()
    profile = state.get("confirmed_profile")
    role = state.get("role_assessment")
    analysis = runtime.context.content_store.get_analysis(state["run_id"])
    if profile is None or role is None or analysis is None:
        limitations = ["Career-assessment synthesis inputs were unavailable."]
        return {
            "current_stage": WorkflowStage.CAREER_ASSESSMENT_SYNTHESIS_READY,
            "career_assessment_synthesis": None,
            "limitations": _unique(state.get("limitations", []), limitations),
            "workflow_status": WorkflowStatus.COMPLETED_WITH_LIMITATIONS,
            "degraded_mode": True,
            "completed_stages": _completed(state, WorkflowStage.CAREER_ASSESSMENT_SYNTHESIS)
            + [WorkflowStage.CAREER_ASSESSMENT_SYNTHESIS_READY],
            "updated_at": runtime.context.clock(),
        }
    synthesis = runtime.context.career_synthesis_service(
        profile, role, analysis, runtime.context.model_gateway
    )
    updated_role = role.model_copy(
        update={
            "candidate_accessibility": synthesis.accessibility,
            "explanation": synthesis.accessibility_rationale,
            "confidence": synthesis.confidence,
        }
    )
    limitations = _unique(state.get("limitations", []), synthesis.limitations)
    _log_node(
        runtime,
        run_id=state["run_id"],
        node="career_assessment_synthesis",
        started=started,
        status=synthesis.status,
        limitation_count=len(synthesis.limitations),
        route="career_path",
    )
    return {
        "current_stage": WorkflowStage.CAREER_ASSESSMENT_SYNTHESIS_READY,
        "career_assessment_synthesis": synthesis,
        "role_assessment": updated_role,
        "candidate_accessibility": synthesis.accessibility,
        "limitations": limitations,
        "degraded_mode": bool(synthesis.limitations) or state.get("degraded_mode", False),
        "workflow_status": WorkflowStatus.CANDIDATE_ASSESSMENT_READY,
        "completed_stages": _completed(state, WorkflowStage.CAREER_ASSESSMENT_SYNTHESIS)
        + [WorkflowStage.CAREER_ASSESSMENT_SYNTHESIS_READY],
        "updated_at": runtime.context.clock(),
    }


def timeline_assessment(
    state: CareerGraphState, runtime: Runtime[WorkflowRuntimeContext]
) -> dict[str, object]:
    """Assess the requested timeline after an optional bridge evaluation."""

    profile = state.get("confirmed_profile")
    goal = state.get("confirmed_goal")
    role = state.get("role_assessment")
    snapshot = state.get("market_snapshot")
    analysis = runtime.context.content_store.get_analysis(state["run_id"])
    if not all((profile, goal, role, snapshot, analysis)):
        return {
            "current_stage": WorkflowStage.CAREER_PATH_ASSESSMENT_READY,
            "timeline_analysis_status": TimelineAnalysisStatus.INSUFFICIENT,
            "career_path_limitations": ["Timeline-analysis inputs were unavailable."],
            "workflow_status": WorkflowStatus.COMPLETED_WITH_LIMITATIONS,
            "degraded_mode": True,
            "updated_at": runtime.context.clock(),
        }
    if state.get("bridge_analysis_status") is None:
        bridge = runtime.context.bridge_analysis_service(
            profile, goal, role, analysis, snapshot.related_titles
        )
    else:
        bridge = BridgeAnalysisResult(
            status=state["bridge_analysis_status"],
            outcome=state["bridge_outcome"],
            assessments=state.get("bridge_assessments", []),
            bridge_would_help=state.get("bridge_would_help", False),
            limitations=state.get("career_path_limitations", []),
        )
    result = runtime.context.timeline_analysis_service(goal, role, bridge, snapshot)
    path_limitations = _unique(bridge.limitations, result.limitations)
    limitations = _unique(state.get("limitations", []), path_limitations)
    limited = result.status is not TimelineAnalysisStatus.SUCCEEDED
    return {
        "current_stage": WorkflowStage.CAREER_PATH_ASSESSMENT_READY,
        "bridge_assessments": bridge.assessments,
        "bridge_outcome": bridge.outcome,
        "bridge_analysis_status": bridge.status,
        "bridge_would_help": bridge.bridge_would_help,
        "timeline_assessment": result.assessment,
        "timeline_analysis_status": result.status,
        "career_path_limitations": path_limitations,
        "limitations": limitations,
        "degraded_mode": limited or state.get("degraded_mode", False),
        "workflow_status": (
            WorkflowStatus.COMPLETED_WITH_LIMITATIONS
            if limited or state.get("degraded_mode", False)
            else WorkflowStatus.CAREER_PATH_ASSESSMENT_READY
        ),
        "completed_stages": _completed(state, WorkflowStage.TIMELINE_ASSESSMENT)
        + [WorkflowStage.CAREER_PATH_ASSESSMENT_READY],
        "updated_at": runtime.context.clock(),
    }


def career_plan_generation(
    state: CareerGraphState, runtime: Runtime[WorkflowRuntimeContext]
) -> dict[str, object]:
    """Generate a validated draft plan from the completed path assessment."""

    started = perf_counter()
    profile = state.get("confirmed_profile")
    goal = state.get("confirmed_goal")
    role = state.get("role_assessment")
    bridge_outcome = state.get("bridge_outcome")
    timeline = state.get("timeline_assessment")
    snapshot = state.get("market_snapshot")
    if not all((profile, goal, role, bridge_outcome, timeline, snapshot)):
        limitations = ["Career-plan inputs were unavailable in the active run."]
        return {
            "current_stage": WorkflowStage.CAREER_PLAN_READY,
            "career_plan": None,
            "career_plan_status": PlanGenerationStatus.LIMITED,
            "plan_limitations": limitations,
            "limitations": _unique(state.get("limitations", []), limitations),
            "workflow_status": WorkflowStatus.COMPLETED_WITH_LIMITATIONS,
            "degraded_mode": True,
            "completed_stages": _completed(state, WorkflowStage.CAREER_PLAN_GENERATION)
            + [WorkflowStage.CAREER_PLAN_READY],
            "updated_at": runtime.context.clock(),
        }
    result = runtime.context.career_plan_generation_service(
        profile,
        goal,
        role,
        state.get("bridge_assessments", []),
        bridge_outcome,
        timeline,
        None,
        market_confidence=snapshot.evidence_confidence,
        source_ids=state.get("market_source_ids", []),
        synthesis=state.get("career_assessment_synthesis"),
    )
    limitations = _unique(state.get("limitations", []), result.limitations)
    limited = bool(result.limitations)
    update = {
        "current_stage": WorkflowStage.CAREER_PLAN_READY,
        "career_plan": result.plan,
        "career_plan_status": result.status,
        "plan_limitations": result.limitations,
        "limitations": limitations,
        "workflow_status": WorkflowStatus.WAITING_FOR_HUMAN,
        "human_action_required": HumanAction.FINAL_PLAN_REVIEW,
        "degraded_mode": limited or state.get("degraded_mode", False),
        "completed_stages": _completed(state, WorkflowStage.CAREER_PLAN_GENERATION)
        + [WorkflowStage.CAREER_PLAN_READY],
        "updated_at": runtime.context.clock(),
    }
    analysis = runtime.context.content_store.get_analysis(state["run_id"])
    if analysis is not None:
        try:
            audit_state = {**state, **update}
            update["audit_artifact_path"] = str(
                persist_run_audit(
                    audit_state,
                    analysis,
                    directory=runtime.context.settings.run_audit_directory,
                )
            )
        except OSError as error:
            runtime.context.logger.warning(
                "run_audit_persistence_failed run_id=%s category=%s",
                state["run_id"],
                type(error).__name__,
            )
    _log_node(
        runtime,
        run_id=state["run_id"],
        node="career_plan_generation",
        started=started,
        status=result.status,
        limitation_count=len(result.limitations),
        route="end",
    )
    return update


def final_plan_review(
    state: CareerGraphState, runtime: Runtime[WorkflowRuntimeContext]
) -> dict[str, object]:
    """Pause for an exact-version final plan decision."""

    plan = state.get("career_plan")
    if plan is None:
        return {
            "current_stage": WorkflowStage.FINALIZED,
            "workflow_status": WorkflowStatus.INSUFFICIENT_EVIDENCE,
            "human_action_required": None,
            "completed_at": runtime.context.clock(),
            "last_error": "CAREER_PLAN_UNAVAILABLE",
            "updated_at": runtime.context.clock(),
        }
    runtime.context.logger.info(
        "final_plan_review_opened run_id=%s plan_id=%s plan_version=%d limitation_count=%d",
        state["run_id"],
        plan.plan_id,
        plan.plan_version,
        len(state.get("limitations", [])),
    )
    response = interrupt(
        {
            "action": HumanAction.FINAL_PLAN_REVIEW.value,
            "run_id": str(state["run_id"]),
            "plan_id": str(plan.plan_id),
            "plan_version": plan.plan_version,
            "limitations": list(state.get("limitations", [])),
        }
    )
    try:
        request = PlanReviewRequest.model_validate(response)
    except (TypeError, ValueError):
        request = None
    if (
        request is None
        or request.plan_id != plan.plan_id
        or request.plan_version != plan.plan_version
    ):
        return {
            "current_stage": WorkflowStage.FINAL_PLAN_REVIEW,
            "workflow_status": WorkflowStatus.WAITING_FOR_HUMAN,
            "human_action_required": HumanAction.FINAL_PLAN_REVIEW,
            "plan_review_request": None,
            "last_error": "STALE_OR_INVALID_PLAN_REVIEW",
            "updated_at": runtime.context.clock(),
        }
    runtime.context.logger.info(
        "final_plan_action_selected run_id=%s plan_id=%s plan_version=%d action=%s",
        state["run_id"],
        plan.plan_id,
        plan.plan_version,
        request.action,
    )
    return {
        "current_stage": WorkflowStage.FINAL_PLAN_REVIEW,
        "workflow_status": WorkflowStatus.RUNNING,
        "human_action_required": None,
        "plan_review_request": request,
        "last_error": None,
        "completed_stages": _completed(state, WorkflowStage.FINAL_PLAN_REVIEW),
        "updated_at": runtime.context.clock(),
    }


def finalize_workflow(
    state: CareerGraphState, runtime: Runtime[WorkflowRuntimeContext]
) -> dict[str, object]:
    """Apply a terminal review action without claiming business persistence."""

    request = state.get("plan_review_request")
    plan = state.get("career_plan")
    if request is None or plan is None:
        return {
            "current_stage": WorkflowStage.FINALIZED,
            "workflow_status": WorkflowStatus.FAILED,
            "last_error": "FINALIZATION_INPUT_MISSING",
            "completed_at": runtime.context.clock(),
            "updated_at": runtime.context.clock(),
        }
    timestamp = runtime.context.clock()
    if request.action is PlanReviewAction.APPROVE_AND_SAVE:
        plan = plan.model_copy(
            update={
                "plan_status": PlanStatus.APPROVED,
                "approval_status": ApprovalStatus.APPROVED,
                "approved_at": timestamp,
            }
        )
        final_status = (
            WorkflowStatus.COMPLETED_WITH_LIMITATIONS
            if state.get("degraded_mode", False) or state.get("limitations")
            else WorkflowStatus.COMPLETED
        )
    elif request.action is PlanReviewAction.SAVE_AS_DRAFT:
        final_status = WorkflowStatus.SAVED_AS_DRAFT
    elif request.action is PlanReviewAction.REJECT_RECOMMENDATION:
        plan = plan.model_copy(
            update={
                "plan_status": PlanStatus.REJECTED,
                "approval_status": ApprovalStatus.REJECTED,
                "approved_at": None,
            }
        )
        final_status = WorkflowStatus.COMPLETED
    elif request.action is PlanReviewAction.CANCEL:
        final_status = WorkflowStatus.USER_CANCELLED
    else:
        raise ValueError(f"action is not terminal: {request.action}")
    record = action_record(request, run_id=state["run_id"], timestamp=timestamp)
    runtime.context.logger.info(
        "workflow_finalized run_id=%s action=%s final_status=%s limitation_count=%d",
        state["run_id"],
        request.action,
        final_status,
        len(state.get("limitations", [])),
    )
    return {
        "current_stage": WorkflowStage.FINALIZED,
        "workflow_status": final_status,
        "career_plan": plan,
        "workflow_action_records": [*state.get("workflow_action_records", []), record],
        "human_action_required": None,
        "completed_at": timestamp,
        "completed_stages": _completed(state, WorkflowStage.FINALIZED),
        "updated_at": timestamp,
    }


def apply_revision_request(
    state: CareerGraphState, runtime: Runtime[WorkflowRuntimeContext]
) -> dict[str, object]:
    """Invalidate only the selected dependency branch and return control safely."""

    request = state.get("plan_review_request")
    if request is None or request.action not in REVISION_PLAN_ACTIONS:
        return {
            "workflow_status": WorkflowStatus.FAILED,
            "last_error": "REVISION_INPUT_MISSING",
            "updated_at": runtime.context.clock(),
        }
    timestamp = runtime.context.clock()
    record = action_record(request, run_id=state["run_id"], timestamp=timestamp)
    update = revision_invalidation(state, request.action)
    update.update(
        {
            "plan_review_request": request,
            "workflow_action_records": [*state.get("workflow_action_records", []), record],
            "updated_at": timestamp,
        }
    )
    runtime.context.logger.info(
        "workflow_revision_requested run_id=%s action=%s revision_route=%s",
        state["run_id"],
        request.action,
        update["workflow_status"],
    )
    return update
