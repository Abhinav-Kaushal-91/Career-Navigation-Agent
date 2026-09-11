"""Provider-neutral plan synthesis and service result schemas."""

from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, model_validator

from ai_career_navigator.domain import CareerPlan, MilestoneType


class PlanGenerationStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    SUCCEEDED_WITH_FALLBACK = "SUCCEEDED_WITH_FALLBACK"
    LIMITED = "LIMITED"


def _milestone_wire_schema(schema: dict) -> None:
    keep = {"milestone_key", "action", "measurable_outcome"}
    schema["properties"] = {
        key: value for key, value in schema["properties"].items() if key in keep
    }
    schema["required"] = [key for key in schema.get("required", []) if key in keep]


def _plan_wire_schema(schema: dict) -> None:
    schema["properties"] = {"milestones": schema["properties"]["milestones"]}
    schema["required"] = ["milestones"]


class MilestoneDraftOutput(BaseModel):
    """Model-editable wording for one deterministic milestone slot."""

    model_config = ConfigDict(extra="forbid", json_schema_extra=_milestone_wire_schema)

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

    model_config = ConfigDict(extra="forbid", json_schema_extra=_plan_wire_schema)

    target_role: str | None = None
    bridge_roles: list[str] = Field(default_factory=list, max_length=3)
    milestones: list[MilestoneDraftOutput] = Field(default_factory=list, max_length=64)
    risks: list[str] = Field(default_factory=list, max_length=8)
    assumptions: list[str] = Field(default_factory=list, max_length=8)

    @model_validator(mode="before")
    @classmethod
    def attach_skeleton_metadata(cls, value, info: ValidationInfo):
        if not isinstance(value, dict) or not info.context:
            return value
        skeleton = info.context.get("plan_skeleton")
        if not isinstance(skeleton, dict):
            return value
        value = dict(value)
        for key in ("target_role", "bridge_roles", "risks", "assumptions"):
            value.setdefault(key, skeleton[key])
        by_key = {item["milestone_key"]: item for item in skeleton["milestones"]}
        if isinstance(value.get("milestones"), list):
            rows = []
            for row in value["milestones"]:
                if isinstance(row, dict) and row.get("milestone_key") in by_key:
                    original = by_key[row["milestone_key"]]
                    # Never overwrite returned values: existing identity checks must reject
                    # attempted changes to immutable fields, including legacy full replies.
                    row = {
                        **{
                            k: v
                            for k, v in original.items()
                            if k not in {"action", "measurable_outcome"}
                        },
                        **row,
                    }
                rows.append(row)
            value["milestones"] = rows
        return value


class PlanWordingRejection(BaseModel):
    """Safe, non-durable diagnostics; never includes candidate or provider text."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    milestone_key: str
    field: Literal["action", "measurable_outcome"]
    reason: str


class CareerPlanGenerationResult(BaseModel):
    """Validated plan plus non-durable generation metadata."""

    model_config = ConfigDict(frozen=True)

    status: PlanGenerationStatus
    plan: CareerPlan
    limitations: list[str] = Field(default_factory=list)
    fallback_used: bool = False
    wording_rejections: list[PlanWordingRejection] = Field(default_factory=list)
