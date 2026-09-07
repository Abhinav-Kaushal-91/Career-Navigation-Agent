"""Career-plan and milestone schemas for V1."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from ai_career_navigator.domain.analysis import BridgeRoleAssessment, TimelineAssessment
from ai_career_navigator.domain.enums import (
    ApprovalStatus,
    ConfidenceLevel,
    MilestoneStatus,
    MilestoneType,
    PathType,
    PlanStatus,
)


def _now_utc() -> datetime:
    return datetime.now(UTC)


class PlanMilestone(BaseModel):
    """A measurable action within one career-plan phase."""

    model_config = ConfigDict(frozen=True)

    milestone_id: UUID = Field(default_factory=uuid4)
    phase: str = Field(min_length=1)
    month_start: int = Field(ge=0)
    month_end: int = Field(ge=0)
    milestone_type: MilestoneType
    action: str = Field(min_length=1)
    linked_gap_ids: list[UUID] = Field(default_factory=list)
    linked_requirement_ids: list[UUID] = Field(default_factory=list)
    supporting_evidence_ids: list[UUID] = Field(default_factory=list)
    basis: str | None = None
    demonstrated_strength: str | None = None
    residual_difference: str | None = None
    measurable_outcome: str = Field(min_length=1)
    evidence_to_create: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    status: MilestoneStatus = MilestoneStatus.PLANNED

    @model_validator(mode="after")
    def validate_month_range(self) -> "PlanMilestone":
        if self.month_end < self.month_start:
            raise ValueError("month_end must not precede month_start")
        return self


class CareerPlan(BaseModel):
    """A versioned, reviewable V1 career strategy."""

    model_config = ConfigDict(frozen=True)

    plan_id: UUID = Field(default_factory=uuid4)
    plan_version: int = Field(default=1, ge=1)
    plan_status: PlanStatus = PlanStatus.DRAFT
    path_type: PathType
    current_role: str | None = None
    target_role: str | None = None
    bridge_roles: list[BridgeRoleAssessment] = Field(default_factory=list)
    timeline_assessment: TimelineAssessment | None = None
    milestones: list[PlanMilestone] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    source_ids: list[UUID] = Field(default_factory=list)
    source_goal_id: UUID | None = None
    source_assessment_id: UUID | None = None
    timing_basis: str | None = None
    confidence: ConfidenceLevel
    approval_status: ApprovalStatus = ApprovalStatus.DRAFT
    created_at: AwareDatetime = Field(default_factory=_now_utc)
    approved_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def validate_plan(self) -> "CareerPlan":
        approved = (
            self.plan_status is PlanStatus.APPROVED
            or self.approval_status is ApprovalStatus.APPROVED
        )
        if approved and self.approved_at is None:
            raise ValueError("approved_at is required for an approved plan")
        if self.path_type is PathType.BRIDGE and not self.bridge_roles:
            raise ValueError("a bridge path requires at least one bridge-role assessment")
        return self
