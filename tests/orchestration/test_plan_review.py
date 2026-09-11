import asyncio
from uuid import uuid4

import pytest

from ai_career_navigator.domain import ApprovalStatus, PlanStatus
from ai_career_navigator.market import MarketContentError, MarketSearchResult
from ai_career_navigator.market.mcp.fake_client import FakeMarketSearchClient
from ai_career_navigator.market.schemas import MarketPageContent
from ai_career_navigator.models.providers import FakeModelProvider
from ai_career_navigator.orchestration import (
    CapabilityWorkflowStatus,
    HumanAction,
    PlanReviewAction,
    WorkflowStage,
    WorkflowStatus,
)

from .conftest import make_controller, requirement_json


def _review_controller(*, limited: bool = False):
    result = MarketSearchResult(
        title="AI Solutions Architect",
        url="https://example.com/jobs/ai-architect",
        snippets=["Job description. Requirements. Apply now."],
    )
    page = MarketPageContent(
        url=result.url,
        title=result.title,
        markdown="Job description. Requirements: Python required. Apply now.",
        employer="Example Canada",
        location="Toronto, Canada",
        active_status="ACTIVE",
    )
    second_result = MarketSearchResult(
        title="AI Solutions Architect",
        url="https://example.com/jobs/ai-architect-2",
        snippets=["Job description. Requirements. Apply now."],
    )
    second_page = page.model_copy(
        update={
            "url": second_result.url,
            "employer": "Second Example Canada",
        }
    )
    search_results = [result, second_result]
    content_outcomes = {result.url: page, second_result.url: second_page}
    if limited:
        blocked = MarketSearchResult(
            title="AI Solutions Architect",
            url="https://example.com/jobs/blocked",
            snippets=["Job description. Requirements. Apply now."],
        )
        search_results.append(blocked)
        content_outcomes[blocked.url] = MarketContentError("blocked")
    market = FakeMarketSearchClient(
        search_outcomes=[search_results],
        content_outcomes=content_outcomes,
    )
    controller, store = make_controller(
        FakeModelProvider(outcomes=[requirement_json(), requirement_json()]), market
    )
    return controller, store, market


def _awaiting_review(approved_profile, approved_goal, *, limited: bool = False):
    controller, store, market = _review_controller(limited=limited)
    result = asyncio.run(
        controller.start(
            thread_id=f"review-{uuid4()}",
            confirmed_profile=approved_profile,
            confirmed_goal=approved_goal,
            capability_inference_requested=False,
        )
    )
    assert result.interrupted
    assert result.state["human_action_required"] is HumanAction.FINAL_PLAN_REVIEW
    return controller, store, market, result


def _submit(controller, waiting, action: PlanReviewAction):
    plan = waiting.state["career_plan"]
    return asyncio.run(
        controller.submit_plan_action(
            thread_id=waiting.state["thread_id"],
            plan_id=plan.plan_id,
            plan_version=plan.plan_version,
            action=action,
        )
    )


def test_final_review_interrupt_and_approval_are_checkpointed(
    approved_profile, approved_goal
) -> None:
    controller, _, _, waiting = _awaiting_review(approved_profile, approved_goal)
    draft = waiting.state["career_plan"]

    assert waiting.interrupts == (
        {
            "action": HumanAction.FINAL_PLAN_REVIEW.value,
            "run_id": str(waiting.state["run_id"]),
            "plan_id": str(draft.plan_id),
            "plan_version": draft.plan_version,
            "limitations": waiting.interrupts[0]["limitations"],
        },
    )
    assert any("fewer than two" in note for note in waiting.interrupts[0]["limitations"])
    assert (
        "Semantic synthesis was unavailable; validated deterministic grouping was used."
        in waiting.interrupts[0]["limitations"]
    )
    completed = _submit(controller, waiting, PlanReviewAction.APPROVE_AND_SAVE)

    assert not completed.interrupted
    assert completed.state["current_stage"] is WorkflowStage.FINALIZED
    assert completed.state["workflow_status"] is WorkflowStatus.COMPLETED_WITH_LIMITATIONS
    assert completed.state["career_plan"].plan_status is PlanStatus.APPROVED
    assert completed.state["career_plan"].approval_status is ApprovalStatus.APPROVED
    assert completed.state["career_plan"].approved_at is not None
    assert draft.plan_status is PlanStatus.DRAFT
    assert completed.state["confirmed_profile"] == approved_profile
    assert completed.state["confirmed_goal"] == approved_goal
    assert completed.state["completed_at"] is not None
    assert len(completed.state["workflow_action_records"]) == 1
    assert completed.state["workflow_action_records"][0].action is (
        PlanReviewAction.APPROVE_AND_SAVE
    )
    inspected = controller.inspect(thread_id=waiting.state["thread_id"])
    assert inspected.state["workflow_status"] is WorkflowStatus.COMPLETED_WITH_LIMITATIONS


def test_approval_with_evidence_limitations_completes_with_limitations(
    approved_profile, approved_goal
) -> None:
    controller, _, _, waiting = _awaiting_review(approved_profile, approved_goal, limited=True)

    completed = _submit(controller, waiting, PlanReviewAction.APPROVE_AND_SAVE)

    assert completed.state["workflow_status"] is WorkflowStatus.COMPLETED_WITH_LIMITATIONS
    assert completed.state["limitations"]
    assert completed.state["career_plan"].plan_status is PlanStatus.APPROVED


@pytest.mark.parametrize(
    ("action", "status", "plan_status", "approval_status"),
    [
        (
            PlanReviewAction.SAVE_AS_DRAFT,
            WorkflowStatus.SAVED_AS_DRAFT,
            PlanStatus.DRAFT,
            ApprovalStatus.DRAFT,
        ),
        (
            PlanReviewAction.REJECT_RECOMMENDATION,
            WorkflowStatus.COMPLETED,
            PlanStatus.REJECTED,
            ApprovalStatus.REJECTED,
        ),
        (
            PlanReviewAction.CANCEL,
            WorkflowStatus.USER_CANCELLED,
            PlanStatus.DRAFT,
            ApprovalStatus.DRAFT,
        ),
    ],
)
def test_terminal_plan_actions_preserve_inputs(
    approved_profile,
    approved_goal,
    action,
    status,
    plan_status,
    approval_status,
) -> None:
    controller, _, _, waiting = _awaiting_review(approved_profile, approved_goal)

    completed = _submit(controller, waiting, action)

    assert completed.state["workflow_status"] is status
    assert completed.state["career_plan"].plan_status is plan_status
    assert completed.state["career_plan"].approval_status is approval_status
    assert completed.state["confirmed_profile"] == approved_profile
    assert completed.state["confirmed_goal"] == approved_goal
    assert completed.state["workflow_action_records"][0].action is action


def test_stale_plan_identity_is_rejected_without_resuming(approved_profile, approved_goal) -> None:
    controller, _, _, waiting = _awaiting_review(approved_profile, approved_goal)
    plan = waiting.state["career_plan"]

    with pytest.raises(ValueError, match="does not match"):
        asyncio.run(
            controller.submit_plan_action(
                thread_id=waiting.state["thread_id"],
                plan_id=uuid4(),
                plan_version=plan.plan_version,
                action=PlanReviewAction.APPROVE_AND_SAVE,
            )
        )
    with pytest.raises(ValueError, match="does not match"):
        asyncio.run(
            controller.submit_plan_action(
                thread_id=waiting.state["thread_id"],
                plan_id=plan.plan_id,
                plan_version=plan.plan_version + 1,
                action=PlanReviewAction.APPROVE_AND_SAVE,
            )
        )

    unchanged = controller.inspect(thread_id=waiting.state["thread_id"])
    assert unchanged.interrupted
    assert unchanged.state["career_plan"].plan_status is PlanStatus.DRAFT
    assert unchanged.state["workflow_action_records"] == []


def test_repeated_identical_action_is_idempotent_and_different_action_is_rejected(
    approved_profile, approved_goal
) -> None:
    controller, _, _, waiting = _awaiting_review(approved_profile, approved_goal)
    first = _submit(controller, waiting, PlanReviewAction.APPROVE_AND_SAVE)
    second = _submit(controller, waiting, PlanReviewAction.APPROVE_AND_SAVE)

    assert second.state["completed_at"] == first.state["completed_at"]
    assert second.state["workflow_action_records"] == first.state["workflow_action_records"]
    assert len(second.state["workflow_action_records"]) == 1
    with pytest.raises(ValueError, match="different final plan action"):
        _submit(controller, waiting, PlanReviewAction.CANCEL)


def test_profile_revision_invalidates_candidate_dependent_analysis_only(
    approved_profile, approved_goal
) -> None:
    controller, _, _, waiting = _awaiting_review(approved_profile, approved_goal)
    snapshot = waiting.state["market_snapshot"]
    summary = waiting.state["requirement_summary"]

    revised = _submit(controller, waiting, PlanReviewAction.EDIT_PROFILE_OR_PREFERENCES)

    assert revised.state["workflow_status"] is WorkflowStatus.READY_FOR_PROFILE_REVISION
    assert revised.state["market_snapshot"] == snapshot
    assert revised.state["requirement_summary"] == summary
    assert revised.state["confirmed_profile"] == approved_profile
    assert revised.state["confirmed_goal"] == approved_goal
    assert revised.state["capability_inference_status"] is CapabilityWorkflowStatus.NOT_STARTED
    assert revised.state["inferred_evidence"] == []
    assert revised.state["requirement_comparisons"] == []
    assert revised.state["role_assessment"] is None
    assert revised.state["career_plan"] is None


def test_goal_revision_invalidates_market_and_downstream_only(
    approved_profile, approved_goal
) -> None:
    controller, _, _, waiting = _awaiting_review(approved_profile, approved_goal)
    inference_status = waiting.state["capability_inference_status"]

    revised = _submit(controller, waiting, PlanReviewAction.REVISE_GOAL)

    assert revised.state["workflow_status"] is WorkflowStatus.READY_FOR_GOAL_REVISION
    assert revised.state["confirmed_profile"] == approved_profile
    assert revised.state["confirmed_goal"] == approved_goal
    assert revised.state["capability_inference_status"] is inference_status
    assert revised.state["market_snapshot"] is None
    assert revised.state["requirement_summary"] is None
    assert revised.state["career_plan"] is None


def test_market_reassessment_preserves_inputs_and_does_not_call_market_again(
    approved_profile, approved_goal
) -> None:
    controller, _, market, waiting = _awaiting_review(approved_profile, approved_goal)
    call_count = len(market.search_calls)

    revised = _submit(controller, waiting, PlanReviewAction.REASSESS_MARKET)

    assert revised.state["workflow_status"] is WorkflowStatus.MARKET_REASSESSMENT_REQUESTED
    assert revised.state["confirmed_profile"] == approved_profile
    assert revised.state["confirmed_goal"] == approved_goal
    assert revised.state["market_snapshot"] is None
    assert revised.state["career_plan"] is None
    assert len(market.search_calls) == call_count


def test_analysis_reassessment_preserves_market_and_transient_content(
    approved_profile, approved_goal
) -> None:
    controller, store, _, waiting = _awaiting_review(approved_profile, approved_goal)
    snapshot = waiting.state["market_snapshot"]
    summary = waiting.state["requirement_summary"]
    run_id = waiting.state["run_id"]

    revised = _submit(controller, waiting, PlanReviewAction.REASSESS_CAREER_ANALYSIS)

    assert revised.state["workflow_status"] is (
        WorkflowStatus.CAREER_ANALYSIS_REASSESSMENT_REQUESTED
    )
    assert revised.state["market_snapshot"] == snapshot
    assert revised.state["requirement_summary"] == summary
    assert revised.state["requirement_comparisons"] == []
    assert revised.state["role_assessment"] is None
    assert revised.state["career_plan"] is None
    assert store.get_analysis(run_id) is not None
