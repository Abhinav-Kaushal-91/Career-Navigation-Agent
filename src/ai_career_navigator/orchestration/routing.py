"""Coarse conditional routes for the Activity 5C graph."""

from typing import Literal

from ai_career_navigator.domain import CandidateAccessibility, GapSeverity

from .approval import REVISION_PLAN_ACTIONS, TERMINAL_PLAN_ACTIONS
from .state import (
    CapabilityWorkflowStatus,
    CareerGraphState,
    MarketProcessingWorkflowStatus,
    MarketSearchWorkflowStatus,
    WorkflowStatus,
)


def route_after_profile(state: CareerGraphState) -> Literal["inference", "end"]:
    return "inference" if state["workflow_status"] is WorkflowStatus.RUNNING else "end"


def route_after_inference(state: CareerGraphState) -> Literal["review", "goal"]:
    if state["capability_inference_status"] is CapabilityWorkflowStatus.REVIEW_REQUIRED:
        return "review"
    return "goal"


def route_after_review(state: CareerGraphState) -> Literal["goal", "end"]:
    return "goal" if state["workflow_status"] is WorkflowStatus.RUNNING else "end"


def route_after_goal(state: CareerGraphState) -> Literal["market", "end"]:
    return "market" if state["workflow_status"] is WorkflowStatus.RUNNING else "end"


def route_after_market_retrieval(state: CareerGraphState) -> Literal["processing", "end"]:
    if state["market_search_status"] in {
        MarketSearchWorkflowStatus.SUCCEEDED,
        MarketSearchWorkflowStatus.LIMITED,
    }:
        return "processing"
    return "end"


def route_after_market_processing(state: CareerGraphState) -> Literal["ready", "end"]:
    if state["market_processing_status"] in {
        MarketProcessingWorkflowStatus.SUCCEEDED,
        MarketProcessingWorkflowStatus.LIMITED,
    }:
        return "ready"
    return "end"


def route_after_market_ready(state: CareerGraphState) -> Literal["comparison", "end"]:
    if state["workflow_status"] in {
        WorkflowStatus.MARKET_READY,
        WorkflowStatus.COMPLETED_WITH_LIMITATIONS,
    }:
        return "comparison"
    return "end"


def route_after_candidate_comparison(state: CareerGraphState) -> Literal["gaps", "end"]:
    if state["workflow_status"] in {
        WorkflowStatus.CANDIDATE_COMPARISON_READY,
        WorkflowStatus.COMPLETED_WITH_LIMITATIONS,
    }:
        return "gaps"
    return "end"


def route_after_candidate_assessment(state: CareerGraphState) -> Literal["bridge", "timeline"]:
    role = state.get("role_assessment")
    if role is None:
        return "timeline"
    if role.candidate_accessibility in {
        CandidateAccessibility.APPLY_NOW,
        CandidateAccessibility.INSUFFICIENT_CANDIDATE_EVIDENCE,
    }:
        return "timeline"
    if role.candidate_accessibility is CandidateAccessibility.APPLY_SELECTIVELY and not any(
        item.severity in {GapSeverity.HIGH, GapSeverity.BLOCKING} for item in role.gaps
    ):
        return "timeline"
    return "bridge"


def route_after_plan_review(state: CareerGraphState) -> Literal["finalize", "revision", "end"]:
    request = state.get("plan_review_request")
    if request is None:
        return "end"
    if request.action in TERMINAL_PLAN_ACTIONS:
        return "finalize"
    if request.action in REVISION_PLAN_ACTIONS:
        return "revision"
    return "end"
