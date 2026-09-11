"""Bounded readiness keeps unknowns separate from demonstrated mismatches."""

import pytest

from ai_career_navigator.career import assess_candidate_accessibility, synthesize_career_assessment
from ai_career_navigator.career.evidence_coverage import (
    readiness_coverage_issue,
    readiness_coverage_notes,
)
from ai_career_navigator.domain import CandidateAccessibility, ConfidenceLevel, MatchType
from ai_career_navigator.market.requirement_schemas import (
    CanonicalRequirementKind,
    CanonicalRequirementScope,
    CanonicalRoleRequirement,
    CanonicalTargetRoleProfile,
    RoleProfileStatus,
)
from tests.career.test_gap_analysis import NOW, inputs
from tests.career.test_synthesis import Finding, SynthesisScenario, build_scenario


def scenario(*, total=3, unresolved=(2,), employer_specific=False, failed=False):
    profile, role, market = build_scenario(
        SynthesisScenario(
            "bounded_coverage",
            "Current Role",
            "Target Role",
            tuple(
                Finding(f"Capability {i}", f"Capability {i}", MatchType.DIRECT_MATCH)
                for i in range(total)
            ),
            frozenset(),
        )
    )
    canonical_items = []
    requirements = []
    for i, requirement in enumerate(market.requirements):
        specific = employer_specific and i in unresolved
        requirements.append(requirement.model_copy(update={"employer_specific": specific}))
        canonical_items.append(
            CanonicalRoleRequirement(
                canonical_requirement_id=requirement.requirement_id,
                display_name=requirement.normalized_capability,
                category=requirement.category,
                requirement_kind=CanonicalRequirementKind.CAPABILITY,
                frequency_band="COMMON",
                primary_support_ratio=1,
                employer_support_count=3,
                posting_support_count=3,
                exact_support_count=3,
                variant_support_count=0,
                related_support_count=0,
                supporting_requirement_ids=[requirement.requirement_id],
                supporting_posting_ids=[requirement.posting_id],
                representative_source_quotes=[requirement.requirement_text],
                confidence=ConfidenceLevel.HIGH,
                requirement_scope=CanonicalRequirementScope.CORE,
                employer_specific=specific,
            )
        )
    canonical = CanonicalTargetRoleProfile(
        target_role=role.target_role,
        geography="Canada",
        profile_status=RoleProfileStatus.STABLE,
        confidence=ConfidenceLevel.HIGH,
        exact_posting_count=5,
        variant_posting_count=0,
        related_posting_count=0,
        distinct_exact_employer_count=3,
        analyzed_exact_posting_count=5,
        analyzed_variant_posting_count=0,
        analyzed_related_posting_count=0,
        generated_at=NOW,
        requirements=canonical_items,
    )
    comparisons = [
        item.model_copy(
            update={
                "evidence_status": ("OPERATION_FAILED" if failed else "UNKNOWN")
                if i in unresolved
                else "SUPPORTED",
                "match_type": None if i in unresolved else MatchType.DIRECT_MATCH,
                "confidence": ConfidenceLevel.INSUFFICIENT
                if i in unresolved
                else ConfidenceLevel.HIGH,
                "clarification_needed": "Verify this evidence." if i in unresolved else None,
            }
        )
        for i, item in enumerate(role.requirement_comparisons)
    ]
    return (
        profile,
        role.model_copy(update={"requirement_comparisons": comparisons}),
        market.model_copy(update={"requirements": requirements, "canonical_profile": canonical}),
    )


@pytest.mark.parametrize("employer_specific", [False, True])
@pytest.mark.parametrize("failed", [False, True])
def test_minor_unknown_preserves_assessment_and_specific_questions(employer_specific, failed):
    profile, role, market = scenario(employer_specific=employer_specific, failed=failed)
    assert readiness_coverage_issue(market, role.requirement_comparisons) is None
    notes = readiness_coverage_notes(market, role.requirement_comparisons)
    assert "Capability 2" in " ".join(notes)
    assert ("Processing incomplete" in " ".join(notes)) is failed
    _, goal, snapshot, _, _ = inputs(
        [item.category for item in market.requirements],
        [MatchType.DIRECT_MATCH] * 3,
    )
    goal = goal.model_copy(update={"target_role": role.target_role})
    assessed = assess_candidate_accessibility(
        profile,
        goal,
        snapshot,
        market,
        role.requirement_comparisons,
    ).role_assessment
    synthesis = synthesize_career_assessment(profile, assessed, market, None)
    assert assessed.candidate_accessibility is CandidateAccessibility.APPLY_SELECTIVELY
    assert synthesis.accessibility is CandidateAccessibility.APPLY_SELECTIVELY
    assert synthesis.confidence is ConfidenceLevel.MODERATE
    assert assessed.requirement_comparisons == role.requirement_comparisons
    assert "Capability 2" in " ".join(synthesis.limitations)
    assert "No material target-role gap remains" not in synthesis.accessibility_rationale
    assert synthesis.demonstrated_strengths


@pytest.mark.parametrize("total,unresolved", [(2, (1,)), (4, (2, 3)), (3, (1, 2))])
def test_at_least_two_and_strict_majority_required(total, unresolved):
    _, role, market = scenario(total=total, unresolved=unresolved)
    assert "Core comparison incomplete" in readiness_coverage_issue(
        market, role.requirement_comparisons
    )


def test_unverified_mandatory_baseline_prerequisite_still_blocks():
    _, role, market = scenario()
    items = list(market.canonical_profile.requirements)
    items[2] = items[2].model_copy(
        update={
            "requirement_kind": CanonicalRequirementKind.PREREQUISITE,
            "mandatory_signal": True,
        }
    )
    market = market.model_copy(
        update={
            "canonical_profile": market.canonical_profile.model_copy(
                update={"requirements": items},
            )
        }
    )
    assert "eligibility remains unverified" in readiness_coverage_issue(
        market, role.requirement_comparisons
    )


@pytest.mark.parametrize(
    "updates,reason",
    [
        ({"profile_status": RoleProfileStatus.INSUFFICIENT}, "Limited market coverage"),
        ({"coverage_limitations": ["Low-quality descriptions"]}, "Low-quality descriptions"),
    ],
)
def test_market_quality_safeguards_preserved(updates, reason):
    _, role, market = scenario(unresolved=())
    market = market.model_copy(
        update={
            "canonical_profile": market.canonical_profile.model_copy(
                update=updates,
            )
        }
    )
    assert reason in readiness_coverage_issue(market, role.requirement_comparisons)


def test_fully_resolved_case_can_still_apply_now():
    profile, role, market = scenario(unresolved=())
    result = synthesize_career_assessment(profile, role, market, None)
    assert result.accessibility is CandidateAccessibility.APPLY_NOW
    assert result.confidence is ConfidenceLevel.HIGH


def test_confirmed_no_match_is_resolved_not_unknown():
    _, role, market = scenario(unresolved=())
    comparisons = list(role.requirement_comparisons)
    comparisons[2] = comparisons[2].model_copy(
        update={
            "match_type": MatchType.NO_CONFIRMED_MATCH,
            "evidence_status": "CONFIRMED_UNMET",
        }
    )
    assert readiness_coverage_issue(market, comparisons) is None
    assert readiness_coverage_notes(market, comparisons) == []
