"""Typed result for Activity 6B gap and accessibility analysis."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from ai_career_navigator.domain import RoleAssessment


class GapAnalysisStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    LIMITED = "LIMITED"
    INSUFFICIENT = "INSUFFICIENT"


class GapAnalysisResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    status: GapAnalysisStatus
    role_assessment: RoleAssessment
    limitations: list[str] = Field(default_factory=list)
