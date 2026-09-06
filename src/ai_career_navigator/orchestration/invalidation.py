"""Central dependency-aware invalidation for final-review revision actions."""

from .approval import PlanReviewAction
from .state import (
    CapabilityWorkflowStatus,
    CareerGraphState,
    MarketProcessingWorkflowStatus,
    MarketSearchWorkflowStatus,
    WorkflowStage,
    WorkflowStatus,
)

_PLAN_STAGES = {
    WorkflowStage.BRIDGE_ROLE_ASSESSMENT,
    WorkflowStage.TIMELINE_ASSESSMENT,
    WorkflowStage.CAREER_PATH_ASSESSMENT_READY,
    WorkflowStage.CAREER_PLAN_GENERATION,
    WorkflowStage.CAREER_PLAN_READY,
    WorkflowStage.FINAL_PLAN_REVIEW,
    WorkflowStage.FINALIZED,
}
_ANALYSIS_STAGES = {
    WorkflowStage.CANDIDATE_REQUIREMENT_COMPARISON,
    WorkflowStage.CANDIDATE_COMPARISON_READY,
    WorkflowStage.GAP_AND_ACCESSIBILITY_ANALYSIS,
    WorkflowStage.CANDIDATE_ASSESSMENT_READY,
    WorkflowStage.CAREER_ASSESSMENT_SYNTHESIS,
    WorkflowStage.CAREER_ASSESSMENT_SYNTHESIS_READY,
    *_PLAN_STAGES,
}
_MARKET_STAGES = {
    WorkflowStage.MARKET_RETRIEVAL,
    WorkflowStage.MARKET_PROCESSING,
    WorkflowStage.MARKET_READY,
    *_ANALYSIS_STAGES,
}


def _without_stages(
    state: CareerGraphState, invalidated: set[WorkflowStage]
) -> list[WorkflowStage]:
    return [item for item in state.get("completed_stages", []) if item not in invalidated]


def _plan_and_path_clear() -> dict[str, object]:
    return {
        "bridge_assessments": [],
        "bridge_outcome": None,
        "bridge_analysis_status": None,
        "bridge_would_help": False,
        "timeline_assessment": None,
        "timeline_analysis_status": None,
        "career_path_limitations": [],
        "career_plan": None,
        "career_plan_status": None,
        "plan_limitations": [],
    }


def _candidate_analysis_clear() -> dict[str, object]:
    return {
        "requirement_comparisons": [],
        "candidate_comparison_status": None,
        "comparison_limitations": [],
        "role_assessment": None,
        "career_assessment_synthesis": None,
        "gap_analysis_status": None,
        "candidate_accessibility": None,
        "gap_limitations": [],
        **_plan_and_path_clear(),
    }


def _market_and_downstream_clear() -> dict[str, object]:
    return {
        "market_search_status": MarketSearchWorkflowStatus.NOT_STARTED,
        "market_snapshot": None,
        "market_source_ids": [],
        "market_posting_audits": [],
        "market_processing_status": MarketProcessingWorkflowStatus.NOT_STARTED,
        "requirement_summary": None,
        "canonical_target_role_profile": None,
        "initial_canonical_target_role_profile": None,
        "posting_requirement_audits": [],
        "target_variant_audits": [],
        "target_variant_expansion_attempted": False,
        **_candidate_analysis_clear(),
    }


def revision_invalidation(state: CareerGraphState, action: PlanReviewAction) -> dict[str, object]:
    """Return only the fields invalidated by the selected revision boundary."""

    common: dict[str, object] = {
        "completed_at": None,
        "human_action_required": None,
        "last_error": None,
        "degraded_mode": False,
        "limitations": [],
    }
    if action is PlanReviewAction.EDIT_PROFILE_OR_PREFERENCES:
        return {
            **common,
            "current_stage": WorkflowStage.PROFILE_REVISION_READY,
            "workflow_status": WorkflowStatus.READY_FOR_PROFILE_REVISION,
            "capability_inference_status": CapabilityWorkflowStatus.NOT_STARTED,
            "inferred_evidence": [],
            "inference_review_completed": False,
            "completed_stages": _without_stages(
                state,
                {
                    WorkflowStage.CAPABILITY_INFERENCE,
                    WorkflowStage.CAPABILITY_INFERENCE_REVIEW,
                    *_ANALYSIS_STAGES,
                },
            ),
            **_candidate_analysis_clear(),
        }
    if action is PlanReviewAction.REVISE_GOAL:
        return {
            **common,
            "current_stage": WorkflowStage.GOAL_REVISION_READY,
            "workflow_status": WorkflowStatus.READY_FOR_GOAL_REVISION,
            "completed_stages": _without_stages(state, {WorkflowStage.GOAL_READY, *_MARKET_STAGES}),
            **_market_and_downstream_clear(),
        }
    if action is PlanReviewAction.REASSESS_MARKET:
        return {
            **common,
            "current_stage": WorkflowStage.MARKET_REASSESSMENT_REQUESTED,
            "workflow_status": WorkflowStatus.MARKET_REASSESSMENT_REQUESTED,
            "completed_stages": _without_stages(state, _MARKET_STAGES),
            **_market_and_downstream_clear(),
        }
    if action is PlanReviewAction.REASSESS_CAREER_ANALYSIS:
        return {
            **common,
            "current_stage": WorkflowStage.CAREER_ANALYSIS_REASSESSMENT_REQUESTED,
            "workflow_status": WorkflowStatus.CAREER_ANALYSIS_REASSESSMENT_REQUESTED,
            "completed_stages": _without_stages(state, _ANALYSIS_STAGES),
            **_candidate_analysis_clear(),
        }
    raise ValueError(f"action does not request revision: {action}")
