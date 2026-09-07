"""Provider-neutral schemas for capability inference and human decisions."""

import re
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ai_career_navigator.domain import (
    CareerStage,
    ConfidenceLevel,
    EvidenceMaturity,
)


class InferredCapability(BaseModel):
    """One model-proposed capability grounded in identified evidence."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    capability: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1)
    supporting_evidence_ids: list[UUID] = Field(min_length=1)
    proposed_maturity: EvidenceMaturity
    confidence: ConfidenceLevel
    reasoning_summary: str = Field(min_length=1)
    source_context_summary: str = Field(min_length=1)

    @field_validator("capability", "description", "reasoning_summary", "source_context_summary")
    @classmethod
    def clean_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be blank")
        return cleaned

    @field_validator("capability")
    @classmethod
    def atomic_capability_name(cls, value: str) -> str:
        if len(value.split()) > 6 or re.match(
            r"(?i)^(?:ability to|experience (?:in|with)|knowledge of|"
            r"strong |reusable |various |general )",
            value,
        ):
            raise ValueError("use a concise atomic professional capability name")
        return value

    @field_validator("supporting_evidence_ids")
    @classmethod
    def unique_evidence_ids(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("supporting evidence IDs must be unique")
        return value


class CapabilityInferenceResult(BaseModel):
    """Validated structured model output for capability inference."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    inferred_capabilities: list[InferredCapability] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    unresolved_areas: list[str] = Field(default_factory=list)

    @field_validator("limitations", "unresolved_areas", mode="before")
    @classmethod
    def clean_lists(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]


class InferenceEvidenceContext(BaseModel):
    """Minimal confirmed evidence supplied to the model."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    evidence_id: UUID
    evidence_type: str
    source_reference: str
    capability: str
    description: str
    maturity: EvidenceMaturity
    context: str | None = None
    outcome: str | None = None
    metric: str | None = None


class CapabilityInferenceContext(BaseModel):
    """PII-minimized input for transferable-capability inference."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    current_role: str | None = None
    career_stage: CareerStage
    career_summary: str | None = None
    core_competencies: str | None = None
    evidence: list[InferenceEvidenceContext] = Field(default_factory=list)


class InferenceDecision(StrEnum):
    CONFIRM = "CONFIRM"
    REJECT = "REJECT"
    LEAVE_UNCONFIRMED = "LEAVE_UNCONFIRMED"


class InferenceRunStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    EMPTY = "EMPTY"
    FAILED = "FAILED"
