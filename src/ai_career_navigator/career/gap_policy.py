"""Transparent V1 policy for gap severity and candidate accessibility."""

from dataclasses import dataclass

from ai_career_navigator.domain import (
    CandidateAccessibility,
    ComparisonScope,
    ConfidenceLevel,
    GapSeverity,
    MatchType,
    RequirementCategory,
    RequirementFrequency,
)

COMMON_MINIMUM = 0.60
FREQUENT_MINIMUM = 0.35
OCCASIONAL_MINIMUM = 0.15

HARD_PREREQUISITE_CATEGORIES = {
    RequirementCategory.CREDENTIAL,
    RequirementCategory.WORK_AUTHORIZATION,
    RequirementCategory.LANGUAGE,
}


def frequency_band(value: float | None) -> RequirementFrequency:
    if value is None:
        return RequirementFrequency.INSUFFICIENT_EVIDENCE
    if value >= COMMON_MINIMUM:
        return RequirementFrequency.COMMON
    if value >= FREQUENT_MINIMUM:
        return RequirementFrequency.FREQUENT
    if value >= OCCASIONAL_MINIMUM:
        return RequirementFrequency.OCCASIONAL
    return RequirementFrequency.RARE


def is_hard_blocker(category: RequirementCategory, mandatory: bool, text: str) -> bool:
    if not mandatory:
        return False
    if category in HARD_PREREQUISITE_CATEGORIES:
        return True
    if category is RequirementCategory.EDUCATION:
        normalized = text.casefold()
        return "equivalent experience" not in normalized and "or equivalent" not in normalized
    return False


def gap_severity(
    *,
    match_type: MatchType | None,
    frequency: RequirementFrequency,
    mandatory: bool,
    preferred: bool,
    scope: ComparisonScope,
    hard_blocker: bool,
    confidence: ConfidenceLevel,
) -> GapSeverity:
    if hard_blocker:
        return GapSeverity.BLOCKING
    if (
        confidence is ConfidenceLevel.INSUFFICIENT
        or frequency is RequirementFrequency.INSUFFICIENT_EVIDENCE
    ):
        return GapSeverity.INSUFFICIENT_EVIDENCE
    if scope in {ComparisonScope.RELATED_TITLE, ComparisonScope.COMBINED_RELATED}:
        if frequency is RequirementFrequency.RARE or preferred:
            return GapSeverity.LOW
        return GapSeverity.MODERATE
    if preferred and not mandatory:
        return GapSeverity.LOW
    if frequency is RequirementFrequency.RARE and preferred:
        return GapSeverity.LOW
    if (
        mandatory
        and match_type is MatchType.NO_CONFIRMED_MATCH
        and frequency
        in {
            RequirementFrequency.COMMON,
            RequirementFrequency.FREQUENT,
        }
    ):
        return GapSeverity.HIGH
    if match_type is MatchType.PARTIAL_MATCH and frequency in {
        RequirementFrequency.COMMON,
        RequirementFrequency.FREQUENT,
    }:
        return GapSeverity.HIGH
    if match_type is MatchType.TRANSFERABLE_MATCH and frequency is RequirementFrequency.COMMON:
        return GapSeverity.MODERATE
    if mandatory or frequency is RequirementFrequency.FREQUENT:
        return GapSeverity.MODERATE
    return GapSeverity.LOW


@dataclass(frozen=True)
class AccessibilityInputs:
    exact_comparison_count: int
    exact_supported_count: int
    exact_high_gap_count: int
    exact_moderate_gap_count: int
    blocking_gap_count: int
    insufficient_comparison_count: int
    total_comparison_count: int
    partial_capability_present_count: int = 0
    partial_ownership_scope_count: int = 0
    exact_no_match_count: int = 0


def classify_accessibility(inputs: AccessibilityInputs) -> CandidateAccessibility:
    if not inputs.total_comparison_count or not inputs.exact_comparison_count:
        return CandidateAccessibility.INSUFFICIENT_CANDIDATE_EVIDENCE
    if inputs.insufficient_comparison_count * 2 >= inputs.total_comparison_count:
        return CandidateAccessibility.INSUFFICIENT_CANDIDATE_EVIDENCE
    if inputs.blocking_gap_count:
        return CandidateAccessibility.POOR_FIT
    coverage = inputs.exact_supported_count / inputs.exact_comparison_count
    if inputs.exact_high_gap_count >= 3:
        return (
            CandidateAccessibility.POOR_FIT
            if coverage == 0
            else CandidateAccessibility.ASPIRATIONAL
        )
    if inputs.exact_high_gap_count:
        small_sample_functional_support = (
            inputs.exact_comparison_count <= 3
            and inputs.exact_no_match_count == 0
            and inputs.partial_capability_present_count > 0
        )
        return (
            CandidateAccessibility.NEAR_TERM_TARGET
            if coverage >= 0.5 or small_sample_functional_support
            else CandidateAccessibility.ASPIRATIONAL
        )
    if inputs.exact_moderate_gap_count >= 2:
        return CandidateAccessibility.APPLY_SELECTIVELY
    return CandidateAccessibility.APPLY_NOW
