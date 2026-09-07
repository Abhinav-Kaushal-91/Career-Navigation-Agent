"""Canonical baseline certainty must survive gap analysis and synthesis."""

import pytest

from ai_career_navigator.career import (
    assess_candidate_accessibility,
    synthesize_career_assessment,
)
from ai_career_navigator.domain import (
    CandidateAccessibility,
    ConfidenceLevel,
    MatchType,
    RequirementCategory,
)
from ai_career_navigator.market import CanonicalTargetRoleProfile, RoleProfileStatus
from tests.career.test_gap_analysis import NOW, inputs
from tests.career.test_synthesis import Finding, SynthesisScenario, build_scenario


@pytest.mark.parametrize(
    ("all_direct", "profile_status", "target_confidence"),
    [
        (False, RoleProfileStatus.PROVISIONAL, ConfidenceLevel.LOW),
        (True, RoleProfileStatus.PROVISIONAL, ConfidenceLevel.LOW),
        (False, RoleProfileStatus.STABLE, ConfidenceLevel.HIGH),
        (False, RoleProfileStatus.PROVISIONAL, ConfidenceLevel.MODERATE),
    ],
)
def test_canonical_confidence_caps_three_posting_assessment_without_changing_fit(
    all_direct: bool,
    profile_status: RoleProfileStatus,
    target_confidence: ConfidenceLevel,
) -> None:
    matches = [
        MatchType.DIRECT_MATCH,
        MatchType.DIRECT_MATCH if all_direct else MatchType.PARTIAL_MATCH,
        MatchType.DIRECT_MATCH if all_direct else MatchType.PARTIAL_MATCH,
    ]
    profile, original_role, market = build_scenario(
        SynthesisScenario(
            "generic_canonical_confidence",
            "Service Technician",
            "Technical Specialist",
            tuple(
                Finding(capability, capability, match)
                for capability, match in zip(
                    ["Service Delivery", "Incident Diagnosis", "Technical Documentation"],
                    matches,
                    strict=True,
                )
            ),
            frozenset(),
        )
    )
    _, goal, snapshot, _, _ = inputs([RequirementCategory.TECHNICAL] * 3, matches)
    goal = goal.model_copy(update={"target_role": original_role.target_role})
    snapshot = snapshot.model_copy(update={"target_role": original_role.target_role})
    canonical = CanonicalTargetRoleProfile(
        target_role=original_role.target_role,
        geography=market.summary.geography,
        profile_status=profile_status,
        confidence=target_confidence,
        exact_posting_count=3,
        variant_posting_count=0,
        related_posting_count=0,
        distinct_exact_employer_count=3,
        analyzed_exact_posting_count=3,
        analyzed_variant_posting_count=0,
        analyzed_related_posting_count=0,
        generated_at=NOW,
    )
    assert snapshot.validated_posting_count == 3
    assert snapshot.evidence_confidence is ConfidenceLevel.HIGH
    assert all(
        item.confidence is ConfidenceLevel.HIGH for item in original_role.requirement_comparisons
    )

    uncapped = assess_candidate_accessibility(
        profile, goal, snapshot, market, original_role.requirement_comparisons
    ).role_assessment
    capped_market = market.model_copy(update={"canonical_profile": canonical})
    capped = assess_candidate_accessibility(
        profile, goal, snapshot, capped_market, original_role.requirement_comparisons
    ).role_assessment

    assert uncapped.confidence is ConfidenceLevel.HIGH
    assert capped.confidence is target_confidence
    assert capped.candidate_accessibility is uncapped.candidate_accessibility
    assert capped.requirement_comparisons == uncapped.requirement_comparisons
    assert len(capped.gaps) == len(uncapped.gaps)

    uncapped_synthesis = synthesize_career_assessment(profile, uncapped, market, None)
    capped_synthesis = synthesize_career_assessment(profile, capped, capped_market, None)
    assert uncapped_synthesis.confidence is ConfidenceLevel.HIGH
    assert capped_synthesis.confidence is target_confidence
    assert capped_synthesis.accessibility is uncapped_synthesis.accessibility
    assert capped_synthesis.accessibility is (
        CandidateAccessibility.APPLY_NOW
        if all_direct
        else CandidateAccessibility.NEAR_TERM_TARGET
    )
    if target_confidence is ConfidenceLevel.LOW:
        assert "tentative" in capped_synthesis.accessibility_rationale
