"""Finalization rules for the evidence-first strengths review."""

from datetime import datetime

from ai_career_navigator.domain import CandidateProfile, EvidenceConfirmationStatus
from ai_career_navigator.profile.capabilities import capability_key
from ai_career_navigator.profile.inference import apply_inference_decision
from ai_career_navigator.profile.inference_schemas import InferenceDecision
from ai_career_navigator.profile.schemas import ProfileDraft
from ai_career_navigator.profile.service import confirm_candidate_profile


def finalize_strengths_profile(
    draft: ProfileDraft,
    inference_profile: CandidateProfile,
    selected_capabilities: list[str] | tuple[str, ...],
    *,
    now: datetime | None = None,
) -> CandidateProfile:
    """Rebuild explicit evidence, then retain every inference decision and provenance."""

    base = confirm_candidate_profile(draft, now=now)
    inferred = [
        item
        for item in inference_profile.evidence_items
        if item.confirmation_status
        in {
            EvidenceConfirmationStatus.INFERRED_PENDING,
            EvidenceConfirmationStatus.CONFIRMED_INFERENCE,
            EvidenceConfirmationStatus.REJECTED_INFERENCE,
        }
    ]
    profile = base.model_copy(update={"evidence_items": [*base.evidence_items, *inferred]})
    selected = {capability_key(item) for item in selected_capabilities}
    for item in inferred:
        decision = (
            InferenceDecision.CONFIRM
            if capability_key(item.capability) in selected
            else InferenceDecision.REJECT
        )
        profile = apply_inference_decision(profile, item.evidence_id, decision)
    return profile
