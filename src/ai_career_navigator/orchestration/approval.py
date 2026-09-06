"""Typed final-plan review actions and checkpoint-scoped audit records."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class PlanReviewAction(StrEnum):
    APPROVE_AND_SAVE = "APPROVE_AND_SAVE"
    EDIT_PROFILE_OR_PREFERENCES = "EDIT_PROFILE_OR_PREFERENCES"
    REVISE_GOAL = "REVISE_GOAL"
    REASSESS_MARKET = "REASSESS_MARKET"
    REASSESS_CAREER_ANALYSIS = "REASSESS_CAREER_ANALYSIS"
    REJECT_RECOMMENDATION = "REJECT_RECOMMENDATION"
    SAVE_AS_DRAFT = "SAVE_AS_DRAFT"
    CANCEL = "CANCEL"


class PlanReviewRequest(BaseModel):
    """Exact plan version and action supplied when resuming human review."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    plan_id: UUID
    plan_version: int = Field(ge=1)
    action: PlanReviewAction


class WorkflowActionRecord(BaseModel):
    """Session/checkpoint-scoped record; not durable business persistence."""

    model_config = ConfigDict(frozen=True)

    action_id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    plan_id: UUID
    plan_version: int = Field(ge=1)
    action: PlanReviewAction
    timestamp: AwareDatetime


TERMINAL_PLAN_ACTIONS = frozenset(
    {
        PlanReviewAction.APPROVE_AND_SAVE,
        PlanReviewAction.REJECT_RECOMMENDATION,
        PlanReviewAction.SAVE_AS_DRAFT,
        PlanReviewAction.CANCEL,
    }
)

REVISION_PLAN_ACTIONS = frozenset(set(PlanReviewAction) - TERMINAL_PLAN_ACTIONS)


def action_record(
    request: PlanReviewRequest, *, run_id: UUID, timestamp: datetime
) -> WorkflowActionRecord:
    return WorkflowActionRecord(
        run_id=run_id,
        plan_id=request.plan_id,
        plan_version=request.plan_version,
        action=request.action,
        timestamp=timestamp,
    )
