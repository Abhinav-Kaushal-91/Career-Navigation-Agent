"""Candidate evidence, profile, and career-goal schemas for V1."""

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl, model_validator

from ai_career_navigator.domain.enums import (
    ApprovalStatus,
    CareerStage,
    ConfidenceLevel,
    EvidenceConfirmationStatus,
    EvidenceMaturity,
    GeographyScope,
    GoalType,
)


def _now_utc() -> datetime:
    return datetime.now(UTC)


class EvidenceItem(BaseModel):
    """A traceable item supporting a candidate capability or experience."""

    model_config = ConfigDict(frozen=True)

    evidence_id: UUID = Field(default_factory=uuid4, description="Stable evidence identifier.")
    evidence_type: str = Field(min_length=1, description="Kind of candidate evidence.")
    source_type: str = Field(min_length=1, description="Origin category for the evidence.")
    source_reference: str = Field(min_length=1, description="Reference to the source material.")
    capability: str = Field(min_length=1)
    description: str = Field(min_length=1)
    maturity_level: EvidenceMaturity
    context: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    outcome: str | None = None
    metric: str | None = None
    confirmation_status: EvidenceConfirmationStatus
    confidence: ConfidenceLevel
    approved_by_user: bool = False
    created_at: AwareDatetime = Field(default_factory=_now_utc)

    @model_validator(mode="after")
    def validate_dates_and_confirmation(self) -> "EvidenceItem":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must not precede start_date")
        if (
            self.confirmation_status is EvidenceConfirmationStatus.REJECTED_INFERENCE
            and self.approved_by_user
        ):
            raise ValueError("rejected inference cannot be approved by the user")
        if (
            self.confirmation_status is EvidenceConfirmationStatus.CONFIRMED_INFERENCE
            and not self.approved_by_user
        ):
            raise ValueError("confirmed inference requires user approval")
        return self


class CandidateProfile(BaseModel):
    """A versioned candidate profile composed of structured evidence items."""

    model_config = ConfigDict(frozen=True)

    profile_id: UUID = Field(default_factory=uuid4)
    profile_version: int = Field(default=1, ge=1)
    career_stage: CareerStage
    professional_summary: str | None = None
    core_competencies: str | None = None
    current_role: str | None = None
    current_seniority: str | None = None
    current_location: str | None = None
    evidence_items: list[EvidenceItem] = Field(default_factory=list)
    portfolio_links: list[HttpUrl] = Field(default_factory=list)
    approval_status: ApprovalStatus = ApprovalStatus.DRAFT
    created_at: AwareDatetime = Field(default_factory=_now_utc)
    confirmed_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def validate_approval(self) -> "CandidateProfile":
        if self.approval_status is ApprovalStatus.APPROVED and self.confirmed_at is None:
            raise ValueError("confirmed_at is required for an approved profile")
        return self

    @property
    def approved_evidence_items(self) -> tuple[EvidenceItem, ...]:
        """Return only evidence eligible to support candidate analysis."""

        accepted = {
            EvidenceConfirmationStatus.EXPLICIT,
            EvidenceConfirmationStatus.CONFIRMED_INFERENCE,
        }
        return tuple(
            item
            for item in self.evidence_items
            if item.confirmation_status in accepted and item.approved_by_user
        )


class CareerGoal(BaseModel):
    """A versioned statement of the user's intended career direction."""

    model_config = ConfigDict(frozen=True)

    goal_id: UUID = Field(default_factory=uuid4)
    goal_version: int = Field(default=1, ge=1)
    goal_type: GoalType
    target_role: str | None = None
    target_seniority: str | None = None
    target_timeline_months: int | None = Field(default=None, gt=0)
    target_location: str | None = None
    target_industries: list[str] = Field(default_factory=list)
    preferred_work_modes: list[str] = Field(default_factory=list)
    geography_scopes: list[GeographyScope] = Field(default_factory=list)
    bridge_role_willingness: bool | None = None
    search_expansion_permission: bool = False
    exploration_mode: bool = False
    exclusions: list[str] = Field(default_factory=list)
    approval_status: ApprovalStatus = ApprovalStatus.DRAFT
    created_at: AwareDatetime = Field(default_factory=_now_utc)
    approved_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def validate_goal(self) -> "CareerGoal":
        if self.approval_status is ApprovalStatus.APPROVED and self.approved_at is None:
            raise ValueError("approved_at is required for an approved goal")
        if self.goal_type is GoalType.TARGET_CAREER_PATH and not self.target_role:
            raise ValueError("target_role is required for a target career path")
        if GeographyScope.COUNTRY_REMOTE in self.geography_scopes and "remote" not in {
            mode.casefold() for mode in self.preferred_work_modes
        }:
            raise ValueError("COUNTRY_REMOTE requires Remote as an accepted work mode")
        return self
