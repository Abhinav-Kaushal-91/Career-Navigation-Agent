"""Typed, checkpoint-safe state for the workflow through Activity 7B."""

from datetime import datetime
from enum import StrEnum
from typing import NotRequired, TypedDict
from uuid import UUID

from pydantic import TypeAdapter

from ai_career_navigator.career import (
    BridgeAnalysisStatus,
    CandidateComparisonStatus,
    CareerAssessmentSynthesis,
    GapAnalysisStatus,
    PlanGenerationStatus,
    TimelineAnalysisStatus,
)
from ai_career_navigator.domain import (
    BridgeOutcome,
    BridgeRoleAssessment,
    CandidateAccessibility,
    CandidateProfile,
    CareerGoal,
    CareerPlan,
    CurrentMarketSnapshot,
    EvidenceItem,
    RequirementComparison,
    RoleAssessment,
    TimelineAssessment,
)
from ai_career_navigator.market import (
    CanonicalTargetRoleProfile,
    MarketProviderSummary,
    MarketRequirementSummary,
    PostingRequirementAudit,
    PostingRetrievalAudit,
    TargetVariantAudit,
)
from ai_career_navigator.market.schemas import SearchPassReport

from .approval import PlanReviewRequest, WorkflowActionRecord


class WorkflowStage(StrEnum):
    INITIALIZE = "INITIALIZE"
    PROFILE_READY = "PROFILE_READY"
    CAPABILITY_INFERENCE = "CAPABILITY_INFERENCE"
    CAPABILITY_INFERENCE_REVIEW = "CAPABILITY_INFERENCE_REVIEW"
    GOAL_READY = "GOAL_READY"
    MARKET_RETRIEVAL = "MARKET_RETRIEVAL"
    MARKET_PROCESSING = "MARKET_PROCESSING"
    MARKET_READY = "MARKET_READY"
    CANDIDATE_REQUIREMENT_COMPARISON = "CANDIDATE_REQUIREMENT_COMPARISON"
    CANDIDATE_COMPARISON_READY = "CANDIDATE_COMPARISON_READY"
    GAP_AND_ACCESSIBILITY_ANALYSIS = "GAP_AND_ACCESSIBILITY_ANALYSIS"
    CANDIDATE_ASSESSMENT_READY = "CANDIDATE_ASSESSMENT_READY"
    CAREER_ASSESSMENT_SYNTHESIS = "CAREER_ASSESSMENT_SYNTHESIS"
    CAREER_ASSESSMENT_SYNTHESIS_READY = "CAREER_ASSESSMENT_SYNTHESIS_READY"
    BRIDGE_ROLE_ASSESSMENT = "BRIDGE_ROLE_ASSESSMENT"
    TIMELINE_ASSESSMENT = "TIMELINE_ASSESSMENT"
    CAREER_PATH_ASSESSMENT_READY = "CAREER_PATH_ASSESSMENT_READY"
    CAREER_PLAN_GENERATION = "CAREER_PLAN_GENERATION"
    CAREER_PLAN_READY = "CAREER_PLAN_READY"
    FINAL_PLAN_REVIEW = "FINAL_PLAN_REVIEW"
    PROFILE_REVISION_READY = "PROFILE_REVISION_READY"
    GOAL_REVISION_READY = "GOAL_REVISION_READY"
    MARKET_REASSESSMENT_REQUESTED = "MARKET_REASSESSMENT_REQUESTED"
    CAREER_ANALYSIS_REASSESSMENT_REQUESTED = "CAREER_ANALYSIS_REASSESSMENT_REQUESTED"
    FINALIZED = "FINALIZED"


class WorkflowStatus(StrEnum):
    RUNNING = "RUNNING"
    WAITING_FOR_HUMAN = "WAITING_FOR_HUMAN"
    READY_FOR_PROFILE = "READY_FOR_PROFILE"
    READY_FOR_GOAL = "READY_FOR_GOAL"
    ROLE_DISCOVERY_REQUIRED = "ROLE_DISCOVERY_REQUIRED"
    MARKET_READY = "MARKET_READY"
    CANDIDATE_COMPARISON_READY = "CANDIDATE_COMPARISON_READY"
    CANDIDATE_ASSESSMENT_READY = "CANDIDATE_ASSESSMENT_READY"
    CAREER_PATH_ASSESSMENT_READY = "CAREER_PATH_ASSESSMENT_READY"
    CAREER_PLAN_READY = "CAREER_PLAN_READY"
    READY_FOR_PROFILE_REVISION = "READY_FOR_PROFILE_REVISION"
    READY_FOR_GOAL_REVISION = "READY_FOR_GOAL_REVISION"
    MARKET_REASSESSMENT_REQUESTED = "MARKET_REASSESSMENT_REQUESTED"
    CAREER_ANALYSIS_REASSESSMENT_REQUESTED = "CAREER_ANALYSIS_REASSESSMENT_REQUESTED"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_LIMITATIONS = "COMPLETED_WITH_LIMITATIONS"
    SAVED_AS_DRAFT = "SAVED_AS_DRAFT"
    USER_CANCELLED = "USER_CANCELLED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    FAILED = "FAILED"


class CapabilityWorkflowStatus(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    NOT_REQUESTED = "NOT_REQUESTED"
    EMPTY = "EMPTY"
    FAILED_CONTINUED = "FAILED_CONTINUED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REVIEWED = "REVIEWED"
    COMPLETED = "COMPLETED"


class MarketSearchWorkflowStatus(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    SUCCEEDED = "SUCCEEDED"
    LIMITED = "LIMITED"
    FAILED = "FAILED"
    ROLE_DISCOVERY_REQUIRED = "ROLE_DISCOVERY_REQUIRED"


class MarketProcessingWorkflowStatus(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    SUCCEEDED = "SUCCEEDED"
    LIMITED = "LIMITED"
    FAILED = "FAILED"


class HumanAction(StrEnum):
    CAPABILITY_INFERENCE_REVIEW = "capability_inference_review"
    FINAL_PLAN_REVIEW = "final_plan_review"


class CareerGraphState(TypedDict):
    """Narrow V1 state; runtime dependencies and raw page corpora are excluded."""

    run_id: UUID
    workflow_version: str
    started_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    current_stage: WorkflowStage
    workflow_status: WorkflowStatus
    confirmed_profile: CandidateProfile | None
    confirmed_goal: CareerGoal | None
    capability_inference_requested: bool
    capability_inference_status: CapabilityWorkflowStatus
    inferred_evidence: list[EvidenceItem]
    inference_review_completed: bool
    market_search_status: MarketSearchWorkflowStatus
    market_snapshot: CurrentMarketSnapshot | None
    market_provider_summary: MarketProviderSummary | None
    market_source_ids: list[UUID]
    market_posting_audits: NotRequired[list[PostingRetrievalAudit]]
    market_search_passes: NotRequired[list[SearchPassReport]]
    market_processing_status: MarketProcessingWorkflowStatus
    requirement_summary: MarketRequirementSummary | None
    canonical_target_role_profile: CanonicalTargetRoleProfile | None
    initial_canonical_target_role_profile: CanonicalTargetRoleProfile | None
    posting_requirement_audits: list[PostingRequirementAudit]
    target_variant_audits: list[TargetVariantAudit]
    target_variant_expansion_attempted: bool
    requirement_comparisons: list[RequirementComparison]
    candidate_comparison_status: CandidateComparisonStatus | None
    comparison_limitations: list[str]
    role_assessment: RoleAssessment | None
    career_assessment_synthesis: CareerAssessmentSynthesis | None
    gap_analysis_status: GapAnalysisStatus | None
    candidate_accessibility: CandidateAccessibility | None
    gap_limitations: list[str]
    bridge_assessments: list[BridgeRoleAssessment]
    bridge_outcome: BridgeOutcome | None
    bridge_analysis_status: BridgeAnalysisStatus | None
    bridge_would_help: bool
    timeline_assessment: TimelineAssessment | None
    timeline_analysis_status: TimelineAnalysisStatus | None
    career_path_limitations: list[str]
    career_plan: CareerPlan | None
    career_plan_status: PlanGenerationStatus | None
    plan_limitations: list[str]
    plan_review_request: PlanReviewRequest | None
    workflow_action_records: list[WorkflowActionRecord]
    limitations: list[str]
    warnings: list[str]
    retry_counts: dict[str, int]
    last_error: str | None
    human_action_required: HumanAction | None
    completed_stages: list[WorkflowStage]
    degraded_mode: bool
    thread_id: NotRequired[str]
    audit_artifact_path: NotRequired[str | None]


_STATE_ADAPTER = TypeAdapter(CareerGraphState)


def serialize_graph_state(state: CareerGraphState | dict[str, object]) -> dict[str, object]:
    """Return a JSON-compatible representation for UI/controller boundaries."""

    return _STATE_ADAPTER.dump_python(state, mode="json")
