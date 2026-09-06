import pytest

from ai_career_navigator.career.bridge_policy import material_gaps
from ai_career_navigator.career.gap_policy import (
    AccessibilityInputs,
    classify_accessibility,
    frequency_band,
    gap_severity,
    is_hard_blocker,
)
from ai_career_navigator.domain import (
    CandidateAccessibility,
    ComparisonScope,
    ConfidenceLevel,
    GapSeverity,
    MatchType,
    RequirementCategory,
    RequirementFrequency,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.8, RequirementFrequency.COMMON),
        (0.4, RequirementFrequency.FREQUENT),
        (0.2, RequirementFrequency.OCCASIONAL),
        (0.1, RequirementFrequency.RARE),
        (None, RequirementFrequency.INSUFFICIENT_EVIDENCE),
    ],
)
def test_frequency_bands_are_transparent(value, expected) -> None:
    assert frequency_band(value) is expected


def test_severity_policy_handles_common_mandatory_rare_preferred_and_insufficient() -> None:
    common = gap_severity(
        match_type=MatchType.NO_CONFIRMED_MATCH,
        frequency=RequirementFrequency.COMMON,
        mandatory=True,
        preferred=False,
        scope=ComparisonScope.EXACT_TARGET,
        hard_blocker=False,
        confidence=ConfidenceLevel.HIGH,
    )
    rare = gap_severity(
        match_type=MatchType.NO_CONFIRMED_MATCH,
        frequency=RequirementFrequency.RARE,
        mandatory=False,
        preferred=True,
        scope=ComparisonScope.EXACT_TARGET,
        hard_blocker=False,
        confidence=ConfidenceLevel.HIGH,
    )
    insufficient = gap_severity(
        match_type=None,
        frequency=RequirementFrequency.INSUFFICIENT_EVIDENCE,
        mandatory=False,
        preferred=False,
        scope=ComparisonScope.EXACT_TARGET,
        hard_blocker=False,
        confidence=ConfidenceLevel.INSUFFICIENT,
    )
    assert (common, rare, insufficient) == (
        GapSeverity.HIGH,
        GapSeverity.LOW,
        GapSeverity.INSUFFICIENT_EVIDENCE,
    )


def test_only_non_substitutable_mandatory_prerequisites_block() -> None:
    assert is_hard_blocker(RequirementCategory.CREDENTIAL, True, "CPA required")
    assert not is_hard_blocker(RequirementCategory.CREDENTIAL, False, "AWS preferred")
    assert not is_hard_blocker(
        RequirementCategory.EDUCATION,
        True,
        "Bachelor's degree or equivalent experience",
    )
    assert not is_hard_blocker(RequirementCategory.LEADERSHIP, True, "Lead a team")


def test_blocking_gaps_are_material() -> None:
    gap = type("Gap", (), {"severity": GapSeverity.BLOCKING})()

    assert material_gaps([gap]) == [gap]


@pytest.mark.parametrize(
    ("inputs", "expected"),
    [
        ((5, 5, 0, 0, 0, 0, 5), CandidateAccessibility.APPLY_NOW),
        ((5, 4, 0, 3, 0, 0, 5), CandidateAccessibility.APPLY_SELECTIVELY),
        ((5, 3, 2, 0, 0, 0, 5), CandidateAccessibility.NEAR_TERM_TARGET),
        ((5, 2, 3, 0, 0, 0, 5), CandidateAccessibility.ASPIRATIONAL),
        ((5, 0, 3, 0, 0, 0, 5), CandidateAccessibility.POOR_FIT),
        ((5, 2, 0, 0, 0, 3, 5), CandidateAccessibility.INSUFFICIENT_CANDIDATE_EVIDENCE),
    ],
)
def test_all_accessibility_outcomes(inputs, expected) -> None:
    assert classify_accessibility(AccessibilityInputs(*inputs)) is expected
