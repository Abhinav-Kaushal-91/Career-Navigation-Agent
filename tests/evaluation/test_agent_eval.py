"""Routing accuracy and task-completion-rate for the LangGraph orchestration.

Routing scenarios call the pure conditional-edge functions in
`ai_career_navigator.orchestration.routing` directly against hand-built states,
so they need no model or market calls. Task-completion scenarios drive the real
`CareerWorkflowController` against the fakes already used by
`tests/orchestration/*`, then check the workflow landed on the status a correct
implementation should reach.
"""

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from ai_career_navigator.domain import (
    ApprovalStatus,
    CandidateAccessibility,
    CandidateProfile,
    CareerGoal,
    CareerStage,
    ComparisonScope,
    ConfidenceLevel,
    EvidenceConfirmationStatus,
    EvidenceItem,
    EvidenceMaturity,
    GapCategory,
    GapItem,
    GapSeverity,
    GoalType,
    RequirementFrequency,
    RoleAssessment,
)
from ai_career_navigator.evaluation.agent_eval import (
    RoutingCaseResult,
    WorkflowScenarioResult,
    summarize_routing_accuracy,
    summarize_task_completion,
)
from ai_career_navigator.models.providers import FakeModelProvider
from ai_career_navigator.orchestration import WorkflowStatus
from ai_career_navigator.orchestration.routing import (
    route_after_candidate_assessment,
    route_after_candidate_comparison,
    route_after_goal,
    route_after_inference,
    route_after_market_processing,
    route_after_market_ready,
    route_after_market_retrieval,
    route_after_plan_review,
    route_after_profile,
    route_after_review,
)
from ai_career_navigator.orchestration.state import (
    CapabilityWorkflowStatus,
    MarketProcessingWorkflowStatus,
    MarketSearchWorkflowStatus,
)
from tests.orchestration.conftest import empty_inference_json, make_controller

NOW = datetime(2026, 9, 13, tzinfo=UTC)


def _gap(severity: GapSeverity) -> GapItem:
    requirement_id = uuid4()
    return GapItem(
        requirement_id=requirement_id,
        comparison_scope=ComparisonScope.EXACT_TARGET,
        requirement_frequency=RequirementFrequency.COMMON,
        category=GapCategory.EXPERIENCE,
        target_expectation="Confirmed production ownership.",
        remaining_difference="Confirmed ownership evidence is missing.",
        severity=severity,
        confidence=ConfidenceLevel.HIGH,
    )


def _role(accessibility: CandidateAccessibility, gaps: list[GapItem]) -> RoleAssessment:
    return RoleAssessment(
        target_role="AI Solutions Architect",
        gaps=gaps,
        candidate_accessibility=accessibility,
        explanation="Evidence-grounded assessment.",
        confidence=ConfidenceLevel.HIGH,
    )


_ROUTERS = {
    "route_after_profile": route_after_profile,
    "route_after_inference": route_after_inference,
    "route_after_review": route_after_review,
    "route_after_goal": route_after_goal,
    "route_after_market_retrieval": route_after_market_retrieval,
    "route_after_market_processing": route_after_market_processing,
    "route_after_market_ready": route_after_market_ready,
    "route_after_candidate_comparison": route_after_candidate_comparison,
    "route_after_candidate_assessment": route_after_candidate_assessment,
    "route_after_plan_review": route_after_plan_review,
}


def _routing_scenarios() -> list[RoutingCaseResult]:
    scenarios: list[tuple[str, str, dict, str]] = [
        (
            "route_after_profile",
            "running",
            {"workflow_status": WorkflowStatus.RUNNING},
            "inference",
        ),
        (
            "route_after_profile",
            "not-running",
            {"workflow_status": WorkflowStatus.READY_FOR_PROFILE},
            "end",
        ),
        (
            "route_after_inference",
            "review-required",
            {"capability_inference_status": CapabilityWorkflowStatus.REVIEW_REQUIRED},
            "review",
        ),
        (
            "route_after_inference",
            "no-review-needed",
            {"capability_inference_status": CapabilityWorkflowStatus.EMPTY},
            "goal",
        ),
        (
            "route_after_review",
            "running",
            {"workflow_status": WorkflowStatus.RUNNING},
            "goal",
        ),
        (
            "route_after_review",
            "stopped",
            {"workflow_status": WorkflowStatus.READY_FOR_GOAL},
            "end",
        ),
        (
            "route_after_goal",
            "running",
            {"workflow_status": WorkflowStatus.RUNNING},
            "market",
        ),
        (
            "route_after_market_retrieval",
            "succeeded",
            {"market_search_status": MarketSearchWorkflowStatus.SUCCEEDED},
            "processing",
        ),
        (
            "route_after_market_retrieval",
            "failed",
            {"market_search_status": MarketSearchWorkflowStatus.FAILED},
            "end",
        ),
        (
            "route_after_market_processing",
            "insufficient-evidence",
            {
                "workflow_status": WorkflowStatus.INSUFFICIENT_EVIDENCE,
                "market_processing_status": MarketProcessingWorkflowStatus.SUCCEEDED,
            },
            "end",
        ),
        (
            "route_after_market_processing",
            "succeeded",
            {
                "workflow_status": WorkflowStatus.MARKET_READY,
                "market_processing_status": MarketProcessingWorkflowStatus.SUCCEEDED,
            },
            "ready",
        ),
        (
            "route_after_market_ready",
            "ready",
            {"workflow_status": WorkflowStatus.MARKET_READY},
            "comparison",
        ),
        (
            "route_after_candidate_comparison",
            "ready",
            {"workflow_status": WorkflowStatus.CANDIDATE_COMPARISON_READY},
            "gaps",
        ),
        (
            "route_after_candidate_assessment",
            "apply-now-skips-bridge",
            {"role_assessment": _role(CandidateAccessibility.APPLY_NOW, [])},
            "timeline",
        ),
        (
            "route_after_candidate_assessment",
            "blocking-gap-needs-bridge",
            {
                "role_assessment": _role(
                    CandidateAccessibility.APPLY_SELECTIVELY, [_gap(GapSeverity.BLOCKING)]
                )
            },
            "bridge",
        ),
        (
            "route_after_plan_review",
            "no-request",
            {"plan_review_request": None},
            "end",
        ),
    ]
    return [
        RoutingCaseResult(
            router_name=router_name,
            case_id=case_id,
            expected_route=expected,
            actual_route=_ROUTERS[router_name](state),
        )
        for router_name, case_id, state, expected in scenarios
    ]


def test_routing_accuracy_is_perfect_across_the_scripted_scenario_matrix() -> None:
    results = _routing_scenarios()

    summary = summarize_routing_accuracy(results)
    print(summary.model_dump_json(indent=2))

    assert summary.total_cases == len(results)
    assert summary.accuracy == 1.0
    assert set(summary.per_router_accuracy) == {
        "route_after_profile",
        "route_after_inference",
        "route_after_review",
        "route_after_goal",
        "route_after_market_retrieval",
        "route_after_market_processing",
        "route_after_market_ready",
        "route_after_candidate_comparison",
        "route_after_candidate_assessment",
        "route_after_plan_review",
    }
    assert all(rate == 1.0 for rate in summary.per_router_accuracy.values())


def _profile(*, approval_status: ApprovalStatus) -> CandidateProfile:
    evidence = EvidenceItem(
        evidence_type="skill",
        source_type="manual onboarding",
        source_reference="Skills",
        capability="Python",
        description="Used Python in production automation delivery.",
        maturity_level=EvidenceMaturity.PRODUCTION,
        confirmation_status=EvidenceConfirmationStatus.EXPLICIT,
        confidence=ConfidenceLevel.HIGH,
        approved_by_user=True,
        created_at=NOW,
    )
    return CandidateProfile(
        career_stage=CareerStage.MID_CAREER,
        current_role="Automation Developer",
        evidence_items=[evidence],
        approval_status=approval_status,
        created_at=NOW,
        confirmed_at=NOW if approval_status is ApprovalStatus.APPROVED else None,
    )


def _run(thread_id: str, **start_kwargs) -> str:
    controller, _ = make_controller(FakeModelProvider(outcomes=start_kwargs.pop("outcomes", [])))
    result = asyncio.run(controller.start(thread_id=thread_id, **start_kwargs))
    return str(result.state["workflow_status"])


def _task_completion_scenarios() -> list[WorkflowScenarioResult]:
    approved = _profile(approval_status=ApprovalStatus.APPROVED)
    draft = _profile(approval_status=ApprovalStatus.DRAFT)
    open_goal = CareerGoal(
        goal_type=GoalType.CAREER_EXPLORATION,
        target_role=None,
        target_location="Toronto, Canada",
        approval_status=ApprovalStatus.APPROVED,
        created_at=NOW,
        approved_at=NOW,
    )
    scenarios = [
        ("missing-profile", WorkflowStatus.READY_FOR_PROFILE, {}),
        (
            "unapproved-profile",
            WorkflowStatus.FAILED,
            {"confirmed_profile": draft},
        ),
        (
            "approved-profile-no-goal",
            WorkflowStatus.READY_FOR_GOAL,
            {"confirmed_profile": approved, "outcomes": [empty_inference_json()]},
        ),
        (
            "open-goal-needs-role-discovery",
            WorkflowStatus.ROLE_DISCOVERY_REQUIRED,
            {
                "confirmed_profile": approved,
                "confirmed_goal": open_goal,
                "capability_inference_requested": False,
            },
        ),
    ]
    return [
        WorkflowScenarioResult(
            scenario_id=scenario_id,
            expected_status=str(expected_status),
            actual_status=_run(scenario_id, **kwargs),
        )
        for scenario_id, expected_status, kwargs in scenarios
    ]


def test_scripted_workflow_scenarios_reach_their_expected_status() -> None:
    results = _task_completion_scenarios()

    summary = summarize_task_completion(results)
    print(summary.model_dump_json(indent=2))

    assert summary.total_scenarios == 4
    assert summary.completion_rate == 1.0
