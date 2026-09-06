"""Structured candidate-profile onboarding and grounded inference."""

from ai_career_navigator.profile.capabilities import (
    capability_key,
    clean_capability_name,
    dedupe_capabilities,
)
from ai_career_navigator.profile.inference import (
    CapabilityInferenceOutcome,
    InferenceValidationError,
    add_inferred_evidence,
    apply_inference_decision,
    build_inference_context,
    filter_duplicate_inferences,
    infer_capabilities,
    normalize_capability,
    validate_inference_references,
)
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
from ai_career_navigator.profile.navigation import (
    PROFILE_ONBOARDING_STEPS,
    can_navigate_profile_step,
    next_profile_highest,
    profile_step_states,
)
from ai_career_navigator.profile.schemas import (
    AboutYou,
    CertificationEntry,
    EducationEntry,
    ExperienceEntry,
    ProfileDraft,
    ProjectEntry,
    ProjectStage,
    ProjectType,
    SkillCategory,
    SkillEntry,
)
from ai_career_navigator.profile.service import (
    MATURITY_LABELS,
    build_candidate_profile,
    confirm_candidate_profile,
    maturity_from_label,
    maturity_label,
)
from ai_career_navigator.profile.strengths import finalize_strengths_profile

__all__ = [
    "MATURITY_LABELS",
    "PROMPT_VERSION",
    "PROFILE_ONBOARDING_STEPS",
    "SYSTEM_PROMPT",
    "AboutYou",
    "CapabilityInferenceContext",
    "CapabilityInferenceOutcome",
    "CapabilityInferenceResult",
    "CertificationEntry",
    "EducationEntry",
    "ExperienceEntry",
    "InferenceDecision",
    "InferenceEvidenceContext",
    "InferenceRunStatus",
    "InferenceValidationError",
    "InferredCapability",
    "ProfileDraft",
    "ProjectEntry",
    "ProjectStage",
    "ProjectType",
    "SkillCategory",
    "SkillEntry",
    "add_inferred_evidence",
    "apply_inference_decision",
    "build_candidate_profile",
    "build_inference_context",
    "build_user_prompt",
    "can_navigate_profile_step",
    "capability_key",
    "clean_capability_name",
    "confirm_candidate_profile",
    "filter_duplicate_inferences",
    "finalize_strengths_profile",
    "infer_capabilities",
    "maturity_from_label",
    "maturity_label",
    "next_profile_highest",
    "normalize_capability",
    "dedupe_capabilities",
    "profile_step_states",
    "validate_inference_references",
]
