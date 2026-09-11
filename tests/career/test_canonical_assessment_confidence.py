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
    RequirementStatementType,
)
from ai_career_navigator.market import CanonicalTargetRoleProfile, RoleProfileStatus
from tests.career.test_gap_analysis import NOW, inputs
from tests.career.test_synthesis import Finding, SynthesisScenario, build_scenario


def test_unmatched_preferences_and_duties_do_not_create_hiring_gaps() -> None:
    profile, goal, snapshot, market, comparisons = inputs(
        [RequirementCategory.TECHNICAL] * 3,
        [MatchType.DIRECT_MATCH, MatchType.NO_CONFIRMED_MATCH, MatchType.NO_CONFIRMED_MATCH],
    )
    requirements = list(market.requirements)
    requirements[1] = requirements[1].model_copy(
        update={
            "statement_type": RequirementStatementType.PREFERENCE,
            "preferred": True,
            "mandatory": False,
        }
    )
    requirements[2] = requirements[2].model_copy(
        update={
            "statement_type": RequirementStatementType.ROLE_RESPONSIBILITY,
            "mandatory": False,
        }
    )
    market = market.model_copy(update={"requirements": requirements})
    result = assess_candidate_accessibility(profile, goal, snapshot, market, comparisons)
    assert result.role_assessment.gaps == []
    assert len(result.role_assessment.requirement_comparisons) == 3
    assert result.role_assessment.candidate_accessibility is CandidateAccessibility.APPLY_NOW


@pytest.mark.parametrize(
    ("all_direct", "profile_status", "target_confidence"),
    [
        (False, RoleProfileStatus.PROVISIONAL, ConfidenceLevel.LOW),
        (True, RoleProfileStatus.PROVISIONAL, ConfidenceLevel.LOW),
        (False, RoleProfileStatus.STABLE, ConfidenceLevel.HIGH),
        (False, RoleProfileStatus.PROVISIONAL, ConfidenceLevel.MODERATE),
    ],
)
def test_empty_canonical_profile_withholds_readiness_but_preserves_comparisons(
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
    assert capped.confidence is ConfidenceLevel.INSUFFICIENT
    assert capped.candidate_accessibility is CandidateAccessibility.INSUFFICIENT_CANDIDATE_EVIDENCE
    assert capped.requirement_comparisons == uncapped.requirement_comparisons
    assert len(capped.gaps) == len(uncapped.gaps)

    uncapped_synthesis = synthesize_career_assessment(profile, uncapped, market, None)
    capped_synthesis = synthesize_career_assessment(profile, capped, capped_market, None)
    assert uncapped_synthesis.confidence is ConfidenceLevel.HIGH
    assert capped_synthesis.confidence is ConfidenceLevel.INSUFFICIENT
    assert capped_synthesis.accessibility is CandidateAccessibility.INSUFFICIENT_CANDIDATE_EVIDENCE
    assert "fewer than two" in capped_synthesis.accessibility_rationale
