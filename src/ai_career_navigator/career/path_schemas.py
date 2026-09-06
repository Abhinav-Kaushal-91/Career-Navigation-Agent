"""Typed results for bridge-role and timeline assessment."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from ai_career_navigator.domain import BridgeOutcome, BridgeRoleAssessment, TimelineAssessment


class BridgeAnalysisStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    NOT_REQUIRED = "NOT_REQUIRED"
    LIMITED = "LIMITED"
    INSUFFICIENT = "INSUFFICIENT"


class TimelineAnalysisStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    LIMITED = "LIMITED"
    INSUFFICIENT = "INSUFFICIENT"


class BridgeAnalysisResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    status: BridgeAnalysisStatus
    outcome: BridgeOutcome
    assessments: list[BridgeRoleAssessment] = Field(default_factory=list, max_length=3)
    bridge_would_help: bool = False
    limitations: list[str] = Field(default_factory=list)


class TimelineAnalysisResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    status: TimelineAnalysisStatus
    assessment: TimelineAssessment
    limitations: list[str] = Field(default_factory=list)
