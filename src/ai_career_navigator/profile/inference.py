"""Grounded capability inference, validation, mapping, and human decisions."""

import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from ai_career_navigator.domain import (
    ApprovalStatus,
    CandidateProfile,
    ConfidenceLevel,
    EvidenceConfirmationStatus,
    EvidenceItem,
)
from ai_career_navigator.models import ModelGateway, ModelGatewayError, ModelRole
from ai_career_navigator.profile.capabilities import capability_key
from ai_career_navigator.profile.inference_prompts import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_user_prompt,
)
from ai_career_navigator.profile.inference_schemas import (
    CapabilityInferenceContext,
    CapabilityInferenceResult,
    InferenceDecision,
    InferenceEvidenceContext,
    InferenceRunStatus,
    InferredCapability,
)

logger = logging.getLogger(__name__)


class InferenceValidationError(ValueError):
    """An inference violates evidence-grounding business rules."""


@dataclass(frozen=True)
class CapabilityInferenceOutcome:
    status: InferenceRunStatus
    result: CapabilityInferenceResult
    inferred_evidence: tuple[EvidenceItem, ...] = ()
    error_message: str | None = None
    provider: str | None = None
    model: str | None = None
    latency_ms: float | None = None
    error_category: str | None = None


def build_inference_context(profile: CandidateProfile) -> CapabilityInferenceContext:
    """Select only approved explicit evidence and capability-relevant profile fields."""

    evidence = [
        InferenceEvidenceContext(
            evidence_id=item.evidence_id,
            evidence_type=item.evidence_type,
            source_reference=item.source_reference,
            capability=item.capability,
            description=item.description,
            maturity=item.maturity_level,
            context=item.context,
            outcome=item.outcome,
            metric=item.metric,
        )
        for item in profile.evidence_items
        if item.confirmation_status is EvidenceConfirmationStatus.EXPLICIT and item.approved_by_user
    ]
    return CapabilityInferenceContext(
        current_role=profile.current_role,
        career_stage=profile.career_stage,
        career_summary=profile.professional_summary,
        core_competencies=profile.core_competencies,
        evidence=evidence,
    )


def normalize_capability(value: str) -> str:
    """Apply intentionally narrow normalization for exact duplicate detection."""

    return capability_key(value)


def validate_inference_references(
    result: CapabilityInferenceResult,
    context: CapabilityInferenceContext,
) -> None:
    """Reject syntactically valid but invented evidence identifiers."""

    allowed_ids = {item.evidence_id for item in context.evidence}
    for inference in result.inferred_capabilities:
        unsupported = set(inference.supporting_evidence_ids) - allowed_ids
        if unsupported:
            references = ", ".join(sorted(str(item) for item in unsupported))
            raise InferenceValidationError(f"unsupported evidence reference: {references}")


def filter_duplicate_inferences(
    result: CapabilityInferenceResult,
    profile: CandidateProfile,
) -> CapabilityInferenceResult:
    """Remove exact normalized duplicates without applying semantic similarity."""

    # Every capability already shown or decided in this profile is reserved.
    # This prevents a retry from proposing a confirmed, pending, or rejected
    # item again while retaining deliberately narrow textual matching.
    seen = {normalize_capability(item.capability) for item in profile.evidence_items}
    # Core competencies may be prose grouped under headings. Reserve exact list
    # entries, not fuzzy substrings: related but distinct functions must survive.
    seen.update(
        normalize_capability(entry)
        for entry in re.split(r"[;,:\n\u2022]+", profile.core_competencies or "")
        if entry.strip()
    )
    retained: list[InferredCapability] = []
    for inference in result.inferred_capabilities:
        normalized = normalize_capability(inference.capability)
        if normalized in seen or inference.confidence is ConfidenceLevel.INSUFFICIENT:
            continue
        seen.add(normalized)
        retained.append(inference)
    return result.model_copy(update={"inferred_capabilities": retained})


def _to_evidence(
    inference: InferredCapability,
    *,
    evidence_by_id: dict[UUID, EvidenceItem],
    created_at: datetime,
) -> EvidenceItem:
    sources = [
        f"{item_id} ({evidence_by_id[item_id].source_reference})"
        for item_id in inference.supporting_evidence_ids
    ]
    return EvidenceItem(
        evidence_id=uuid4(),
        evidence_type="inferred capability",
        source_type="AI capability inference",
        source_reference="Supporting evidence: " + "; ".join(dict.fromkeys(sources)),
        capability=inference.capability,
        description=inference.description,
        maturity_level=inference.proposed_maturity,
        confirmation_status=EvidenceConfirmationStatus.INFERRED_PENDING,
        confidence=inference.confidence,
        approved_by_user=False,
        created_at=created_at,
    )


def infer_capabilities(
    profile: CandidateProfile,
    model_gateway: ModelGateway,
    *,
    now: datetime | None = None,
) -> CapabilityInferenceOutcome:
    """Infer additional capabilities without changing the confirmed base profile."""

    if profile.approval_status is not ApprovalStatus.APPROVED:
        raise InferenceValidationError("capability inference requires an approved profile")

    context = build_inference_context(profile)
    empty = CapabilityInferenceResult()
    if not context.evidence:
        return CapabilityInferenceOutcome(status=InferenceRunStatus.EMPTY, result=empty)

    logger.info(
        "capability_inference_started role=%s evidence_count=%d prompt_version=%s",
        ModelRole.EXTRACTION.value,
        len(context.evidence),
        PROMPT_VERSION,
    )
    try:
        response = model_gateway.generate_structured(
            role=ModelRole.EXTRACTION,
            output_schema=CapabilityInferenceResult,
            validation_context={
                "allowed_evidence_ids": tuple(item.evidence_id for item in context.evidence)
            },
            system_prompt=SYSTEM_PROMPT,
            user_prompt=build_user_prompt(context),
            temperature=0,
            max_tokens=10000,
            metadata={
                "task_type": "capability_inference",
                "prompt_version": PROMPT_VERSION,
                "evidence_count": len(context.evidence),
            },
        )
        result = CapabilityInferenceResult.model_validate(response.structured_output)
        validate_inference_references(result, context)
        result = filter_duplicate_inferences(result, profile)
        evidence_by_id = {item.evidence_id: item for item in profile.evidence_items}
        created_at = now or datetime.now(UTC)
        inferred = tuple(
            _to_evidence(item, evidence_by_id=evidence_by_id, created_at=created_at)
            for item in result.inferred_capabilities
        )
    except (ModelGatewayError, InferenceValidationError, TypeError, ValueError) as error:
        logger.warning(
            "capability_inference_failed role=%s evidence_count=%d category=%s",
            ModelRole.EXTRACTION.value,
            len(context.evidence),
            type(error).__name__,
        )
        return CapabilityInferenceOutcome(
            status=InferenceRunStatus.FAILED,
            result=empty,
            error_category=type(error).__name__,
            error_message=(
                "We couldn’t identify additional capabilities right now. Your confirmed "
                "profile is still available and you can continue."
            ),
        )

    status = InferenceRunStatus.SUCCEEDED if inferred else InferenceRunStatus.EMPTY
    logger.info(
        "capability_inference_succeeded provider=%s model=%s role=%s latency_ms=%.2f "
        "evidence_count=%d inferred_count=%d",
        response.provider,
        response.model,
        ModelRole.EXTRACTION.value,
        response.latency_ms,
        len(context.evidence),
        len(inferred),
    )
    return CapabilityInferenceOutcome(
        status=status,
        result=result,
        inferred_evidence=inferred,
        provider=response.provider,
        model=response.model,
        latency_ms=response.latency_ms,
    )


def add_inferred_evidence(
    profile: CandidateProfile, evidence: tuple[EvidenceItem, ...]
) -> CandidateProfile:
    """Return a new approved profile version with pending inference records appended."""

    seen = {normalize_capability(item.capability) for item in profile.evidence_items}
    additions: list[EvidenceItem] = []
    for item in evidence:
        normalized = normalize_capability(item.capability)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        additions.append(item)
    return profile.model_copy(update={"evidence_items": [*profile.evidence_items, *additions]})


def apply_inference_decision(
    profile: CandidateProfile,
    evidence_id: UUID,
    decision: InferenceDecision,
) -> CandidateProfile:
    """Apply a human decision to one inferred item without altering profile approval."""

    found = False
    updated: list[EvidenceItem] = []
    for item in profile.evidence_items:
        if item.evidence_id != evidence_id:
            updated.append(item)
            continue
        found = True
        if item.confirmation_status not in {
            EvidenceConfirmationStatus.INFERRED_PENDING,
            EvidenceConfirmationStatus.CONFIRMED_INFERENCE,
            EvidenceConfirmationStatus.REJECTED_INFERENCE,
        }:
            raise InferenceValidationError(
                "human inference decisions cannot modify explicit evidence"
            )
        if decision is InferenceDecision.LEAVE_UNCONFIRMED:
            replacement = item.model_copy(
                update={
                    "confirmation_status": EvidenceConfirmationStatus.INFERRED_PENDING,
                    "approved_by_user": False,
                }
            )
        elif decision is InferenceDecision.CONFIRM:
            replacement = item.model_copy(
                update={
                    "confirmation_status": EvidenceConfirmationStatus.CONFIRMED_INFERENCE,
                    "approved_by_user": True,
                }
            )
        else:
            replacement = item.model_copy(
                update={
                    "confirmation_status": EvidenceConfirmationStatus.REJECTED_INFERENCE,
                    "approved_by_user": False,
                }
            )
        updated.append(replacement)
    if not found:
        raise InferenceValidationError("inferred evidence item was not found")
    return profile.model_copy(update={"evidence_items": updated})
