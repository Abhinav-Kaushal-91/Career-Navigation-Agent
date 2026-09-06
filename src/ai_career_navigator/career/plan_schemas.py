"""Provider-neutral plan synthesis and service result schemas."""

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ai_career_navigator.domain import CareerPlan, MilestoneType


class PlanGenerationStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    SUCCEEDED_WITH_FALLBACK = "SUCCEEDED_WITH_FALLBACK"
    LIMITED = "LIMITED"


class MilestoneDraftOutput(BaseModel):
    """Model-editable wording for one deterministic milestone slot."""

    model_config = ConfigDict(extra="forbid")

    milestone_key: str = Field(min_length=1)
    phase: str = Field(min_length=1)
    milestone_type: MilestoneType
    action: str = Field(min_length=1)
    linked_gap_ids: list[UUID] = Field(default_factory=list)
    measurable_outcome: str = Field(min_length=1)
    evidence_to_create: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)


class CareerPlanDraftOutput(BaseModel):
    """Bounded model output that cannot set durable plan identity or approval."""

    model_config = ConfigDict(extra="forbid")

    target_role: str | None = None
    bridge_roles: list[str] = Field(default_factory=list, max_length=3)
    milestones: list[MilestoneDraftOutput] = Field(default_factory=list, max_length=12)
    risks: list[str] = Field(default_factory=list, max_length=8)
    assumptions: list[str] = Field(default_factory=list, max_length=8)


class CareerPlanGenerationResult(BaseModel):
    """Validated plan plus non-durable generation metadata."""

    model_config = ConfigDict(frozen=True)

    status: PlanGenerationStatus
    plan: CareerPlan
    limitations: list[str] = Field(default_factory=list)
    fallback_used: bool = False
