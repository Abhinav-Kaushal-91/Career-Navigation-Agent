"""Provider-neutral schemas for capability inference and human decisions."""

import logging
import re
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from ai_career_navigator.domain import (
    CareerStage,
    ConfidenceLevel,
    EvidenceMaturity,
)
from ai_career_navigator.models.output_text import unique_statements

logger = logging.getLogger(__name__)


class InferredCapability(BaseModel):
    """One model-proposed capability grounded in identified evidence."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    capability: str = Field(
        min_length=1,
        max_length=80,
        description="Atomic reusable professional capability, not a named solution or project.",
    )
    description: str = Field(min_length=1, max_length=320, description="One concise sentence.")
    supporting_evidence_ids: list[UUID] = Field(min_length=1)
    proposed_maturity: EvidenceMaturity
    confidence: ConfidenceLevel

    @field_validator("capability", "description")
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

    @field_validator("supporting_evidence_ids", mode="before")
    @classmethod
    def resolve_evidence_prefixes(cls, value: object, info: ValidationInfo) -> object:
        """Repair unique hex prefixes only within this request's explicit evidence."""
        if not isinstance(value, list) or not info.context:
            return value
        allowed = {str(item) for item in info.context.get("allowed_evidence_ids", ())}
        resolved = []
        repairs = 0
        for item in value:
            if str(item) in allowed:
                resolved.append(str(item))
                continue
            if not isinstance(item, str) or not re.fullmatch(r"[0-9a-fA-F-]+", item):
                raise ValueError("evidence ID must exactly match or be a unique supplied prefix")
            prefix = item.lower()
            # Hyphens, if present, must occupy canonical UUID positions.
            compact = prefix.replace("-", "")
            if len(compact) < 8 or len(compact) >= 32:
                raise ValueError("evidence prefix must contain 8 to 31 hexadecimal characters")
            if "-" in prefix:
                matches = [full for full in allowed if full.startswith(prefix)]
            else:
                matches = [full for full in allowed if full.replace("-", "").startswith(prefix)]
            if len(matches) != 1:
                raise ValueError("evidence prefix must uniquely match supplied evidence")
            resolved.append(matches[0])
            repairs += 1
        if repairs:
            logger.info("capability_evidence_id_prefix_repaired count=%d", repairs)
        return resolved


class CapabilityInferenceResult(BaseModel):
    """Validated structured model output for capability inference."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    inferred_capabilities: list[InferredCapability] = Field(default_factory=list)
    limitations: list[str] = Field(
        default_factory=list,
        description=(
            "Evidence-grounded ambiguities affecting returned suggestions only; "
            "no speculative credibility caveats. Empty is valid."
        ),
    )
    unresolved_areas: list[str] = Field(
        default_factory=list,
        description=(
            "Material uncertainties affecting returned capabilities, not generic requests "
            "for more evidence. Empty is valid."
        ),
    )

    @field_validator("limitations", "unresolved_areas", mode="before")
    @classmethod
    def clean_lists(cls, value: list[str]) -> list[str]:
        return unique_statements(value)


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
