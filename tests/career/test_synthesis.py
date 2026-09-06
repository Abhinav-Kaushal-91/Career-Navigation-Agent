"""Generic career-synthesis regression scenarios with no target-role special cases."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from ai_career_navigator.career import (
    CareerGapDimension,
    CareerSynthesisStatus,
    TargetAlignmentType,
    synthesize_career_assessment,
)
from ai_career_navigator.domain import (
    ApprovalStatus,
    CandidateAccessibility,
    CandidateProfile,
    CareerStage,
    ComparisonScope,
    ConfidenceLevel,
    EvidenceConfirmationStatus,
    EvidenceItem,
    EvidenceMaturity,
    GapCategory,
    GapItem,
    GapSeverity,
    MatchType,
    MaturityAlignment,
    PartialMatchSubtype,
    ProductionContextDifference,
    RequirementCategory,
    RequirementComparison,
    RequirementFrequency,
    RoleAssessment,
    RoleRequirement,
)
from ai_career_navigator.market import (
    AggregatedRequirement,
    MarketRequirementAnalysis,
    MarketRequirementSummary,
    RequirementRunStatus,
)
from ai_career_navigator.models import ModelGateway, ModelRole
from ai_career_navigator.models.providers import FakeModelProvider

NOW = datetime(2026, 9, 5, tzinfo=UTC)


@dataclass(frozen=True)
class Finding:
    requirement: str
    candidate_capability: str | None
    match: MatchType
    gap_category: GapCategory = GapCategory.EXPERIENCE
    severity: GapSeverity = GapSeverity.HIGH
    requirement_category: RequirementCategory = RequirementCategory.EXPERIENCE


@dataclass(frozen=True)
class SynthesisScenario:
    name: str
    current_role: str
    target_role: str
    findings: tuple[Finding, ...]
    allowed_accessibility: frozenset[CandidateAccessibility]


SCENARIOS = (
    SynthesisScenario(
        "ai_product_manager",
        "Senior Automation Consultant",
        "AI Product Manager",
        (
            Finding("Product Discovery", "Process Discovery", MatchType.TRANSFERABLE_MATCH),
            Finding("Technical Fluency", "AI Agent Development", MatchType.DIRECT_MATCH),
            Finding(
                "Cross-functional Leadership",
                "Stakeholder Leadership",
                MatchType.DIRECT_MATCH,
            ),
            Finding("Product Vision Ownership", "Solution Roadmaps", MatchType.PARTIAL_MATCH),
        ),
        frozenset({CandidateAccessibility.NEAR_TERM_TARGET}),
    ),
    SynthesisScenario(
        "engineering_manager",
        "Senior Software Engineer",
        "Engineering Manager",
        (
            Finding(
                "Software Delivery",
                "Software Delivery",
                MatchType.DIRECT_MATCH,
                requirement_category=RequirementCategory.TECHNICAL,
            ),
            Finding(
                "Team Coaching",
                "Informal Mentoring",
                MatchType.PARTIAL_MATCH,
                GapCategory.LEADERSHIP_SCOPE,
                GapSeverity.MODERATE,
                RequirementCategory.LEADERSHIP,
            ),
            Finding(
                "Hiring Ownership",
                None,
                MatchType.NO_CONFIRMED_MATCH,
                requirement_category=RequirementCategory.LEADERSHIP,
            ),
            Finding(
                "Performance Management",
                None,
                MatchType.NO_CONFIRMED_MATCH,
                requirement_category=RequirementCategory.LEADERSHIP,
            ),
        ),
        frozenset({CandidateAccessibility.ASPIRATIONAL}),
    ),
    SynthesisScenario(
        "business_analyst_to_product_manager",
        "Business Analyst",
        "Product Manager",
        (
            Finding("Product Discovery", "Process Discovery", MatchType.TRANSFERABLE_MATCH),
            Finding(
                "Requirements Translation",
                "Requirements Translation",
                MatchType.TRANSFERABLE_MATCH,
            ),
            Finding(
                "Stakeholder Communication",
                "Stakeholder Communication",
                MatchType.DIRECT_MATCH,
            ),
            Finding("Roadmap Ownership", "Solution Roadmaps", MatchType.PARTIAL_MATCH),
            Finding("KPI Ownership", None, MatchType.NO_CONFIRMED_MATCH),
            Finding("Product Lifecycle Ownership", None, MatchType.NO_CONFIRMED_MATCH),
        ),
        frozenset(
            {
                CandidateAccessibility.NEAR_TERM_TARGET,
                CandidateAccessibility.ASPIRATIONAL,
            }
        ),
    ),
    SynthesisScenario(
        "data_analyst_to_data_scientist",
        "Data Analyst",
        "Data Scientist",
        (
            Finding(
                "Statistical Analysis",
                "Statistical Analysis",
                MatchType.DIRECT_MATCH,
                requirement_category=RequirementCategory.TECHNICAL,
            ),
            Finding(
                "SQL",
                "SQL",
                MatchType.DIRECT_MATCH,
                requirement_category=RequirementCategory.TECHNICAL,
            ),
            Finding(
                "Machine Learning",
                "ML Coursework",
                MatchType.PARTIAL_MATCH,
                requirement_category=RequirementCategory.TECHNICAL,
            ),
            Finding(
                "Production ML",
                None,
                MatchType.NO_CONFIRMED_MATCH,
                requirement_category=RequirementCategory.TECHNICAL,
            ),
        ),
        frozenset({CandidateAccessibility.NEAR_TERM_TARGET}),
    ),
    SynthesisScenario(
        "student_to_junior_business_analyst",
        "Student",
        "Junior Business Analyst",
        (
            Finding(
                "Requirements Analysis",
                "Academic Requirements Project",
                MatchType.PARTIAL_MATCH,
            ),
            Finding(
                "Stakeholder Communication",
                "Student Society Facilitation",
                MatchType.TRANSFERABLE_MATCH,
            ),
            Finding("Documentation", "Project Documentation", MatchType.DIRECT_MATCH),
        ),
        frozenset({CandidateAccessibility.NEAR_TERM_TARGET}),
    ),
)


def build_scenario(
    scenario: SynthesisScenario,
) -> tuple[CandidateProfile, RoleAssessment, MarketRequirementAnalysis]:
    evidence_items: list[EvidenceItem] = []
    requirements: list[RoleRequirement] = []
    aggregates: list[AggregatedRequirement] = []
    comparisons: list[RequirementComparison] = []
    gaps: list[GapItem] = []
    for finding in scenario.findings:
        posting_id = uuid4()
        requirement = RoleRequirement(
            posting_id=posting_id,
            category=finding.requirement_category,
            requirement_text=finding.requirement,
            normalized_capability=finding.requirement,
            mandatory=True,
            maturity_expected=EvidenceMaturity.PRODUCTION,
            frequency_within_sample=0.75,
            extraction_confidence=ConfidenceLevel.HIGH,
        )
        requirements.append(requirement)
        aggregates.append(
            AggregatedRequirement(
                category=finding.requirement_category,
                normalized_capability=finding.requirement,
                requirement_ids=[requirement.requirement_id],
                exact_title_occurrence_count=1,
                related_title_occurrence_count=0,
                exact_title_frequency=0.75,
                combined_frequency=0.75,
            )
        )
        evidence_ids = []
        candidate_maturity = (
            None
            if finding.match is MatchType.NO_CONFIRMED_MATCH
            else EvidenceMaturity.DEMONSTRATED
            if finding.match is MatchType.PARTIAL_MATCH
            else EvidenceMaturity.PRODUCTION
        )
        if finding.candidate_capability:
            evidence_item = EvidenceItem(
                evidence_type="project" if scenario.name.startswith("student") else "experience",
                source_type="confirmed profile",
                source_reference=scenario.name,
                capability=finding.candidate_capability,
                description=f"Demonstrated {finding.candidate_capability} in a bounded context.",
                maturity_level=candidate_maturity,
                confirmation_status=EvidenceConfirmationStatus.EXPLICIT,
                confidence=ConfidenceLevel.HIGH,
                approved_by_user=True,
                created_at=NOW,
            )
            evidence_items.append(evidence_item)
            evidence_ids = [evidence_item.evidence_id]
        comparison = RequirementComparison(
            requirement_id=requirement.requirement_id,
            posting_id=posting_id,
            comparison_scope=ComparisonScope.EXACT_TARGET,
            evidence_ids=evidence_ids,
            candidate_maturity=candidate_maturity,
            target_maturity=EvidenceMaturity.PRODUCTION,
            match_type=finding.match,
            transferable_capability=finding.candidate_capability,
            remaining_difference=(
                None
                if finding.match in {MatchType.DIRECT_MATCH, MatchType.TRANSFERABLE_MATCH}
                else (
                    f"Confirmed demonstrated evidence is below the required production maturity "
                    f"for {finding.requirement}."
                    if finding.match is MatchType.PARTIAL_MATCH
                    else f"No confirmed evidence exists for {finding.requirement}."
                )
            ),
            explanation=f"Grounded comparison for {finding.requirement}.",
            confidence=ConfidenceLevel.HIGH,
        )
        comparisons.append(comparison)
        if finding.match in {MatchType.PARTIAL_MATCH, MatchType.NO_CONFIRMED_MATCH}:
            gaps.append(
                GapItem(
                    requirement_id=requirement.requirement_id,
                    requirement_ids=[requirement.requirement_id],
                    comparison_scope=ComparisonScope.EXACT_TARGET,
                    requirement_frequency=RequirementFrequency.COMMON,
                    category=finding.gap_category,
                    current_evidence_ids=evidence_ids,
                    current_maturity=candidate_maturity,
                    target_expectation=finding.requirement,
                    remaining_difference=(
                        f"Confirmed demonstrated evidence is below the required production "
                        f"maturity for {finding.requirement}."
                        if finding.match is MatchType.PARTIAL_MATCH
                        else f"No confirmed evidence exists for {finding.requirement}."
                    ),
                    severity=finding.severity,
                    evidence_needed=f"A verified example of {finding.requirement} ownership.",
                    confidence=ConfidenceLevel.HIGH,
                )
            )
    profile = CandidateProfile(
        career_stage=CareerStage.MID_CAREER,
        current_role=scenario.current_role,
        evidence_items=evidence_items,
        approval_status=ApprovalStatus.APPROVED,
        confirmed_at=NOW,
    )
    role = RoleAssessment(
        target_role=scenario.target_role,
        requirement_comparisons=comparisons,
        gaps=gaps,
        candidate_accessibility=CandidateAccessibility.INSUFFICIENT_CANDIDATE_EVIDENCE,
        explanation="Grounded requirement comparisons are ready for career synthesis.",
        confidence=ConfidenceLevel.HIGH,
    )
    count = len(requirements)
    summary = MarketRequirementSummary(
        target_role=scenario.target_role,
        geography="Canada",
        source_page_count=count,
        identified_candidate_count=count,
        validated_in_scope_posting_count=count,
        analyzed_posting_count=count,
        exact_title_analyzed_count=count,
        related_title_analyzed_count=0,
        out_of_scope_count=0,
        unclear_geography_count=0,
        irrelevant_title_count=0,
        requirements=aggregates,
    )
    analysis = MarketRequirementAnalysis(
        status=RequirementRunStatus.SUCCEEDED,
        requirements=requirements,
        summary=summary,
    )
    return profile, role, analysis


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda item: item.name)
def test_generic_synthesis_scenarios_preserve_grounding(
    scenario: SynthesisScenario,
) -> None:
    profile, role, analysis = build_scenario(scenario)

    result = synthesize_career_assessment(profile, role, analysis, None)

    material_ids = {
        item.gap_id
        for item in role.gaps
        if item.severity in {GapSeverity.MODERATE, GapSeverity.HIGH, GapSeverity.BLOCKING}
    }
    grouped_ids = [gap_id for group in result.grouped_gaps for gap_id in group.underlying_gap_ids]
    approved_ids = {item.evidence_id for item in profile.approved_evidence_items}
    assert result.target_role == scenario.target_role
    assert result.accessibility in scenario.allowed_accessibility
    assert result.status is CareerSynthesisStatus.SUCCEEDED_WITH_FALLBACK
    assert len(grouped_ids) == len(set(grouped_ids))
    assert set(grouped_ids) == material_ids
    assert set(result.source_gap_ids) == material_ids
    assert set(result.source_evidence_ids).issubset(approved_ids)
    assert all(
        item.supporting_comparison_ids
        for item in [*result.strongest_advantages, *result.transferable_strengths]
    )
    assert "certification" not in result.assessment_summary.casefold()
    assert "months" not in result.accessibility_rationale.casefold()


def test_product_vision_ownership_is_not_promoted_to_transferable() -> None:
    scenario = SCENARIOS[0]
    _, role, _ = build_scenario(scenario)
    product_vision = next(
        item for item in role.requirement_comparisons if item.remaining_difference
    )

    assert product_vision.match_type is MatchType.PARTIAL_MATCH


def test_product_discovery_can_remain_a_grounded_transferable_match() -> None:
    scenario = SCENARIOS[0]
    _, role, _ = build_scenario(scenario)
    discovery = role.requirement_comparisons[0]

    assert discovery.match_type is MatchType.TRANSFERABLE_MATCH


def test_partial_match_remains_a_demonstrated_strength_without_changing_accessibility() -> None:
    profile, role, analysis = build_scenario(SCENARIOS[0])

    result = synthesize_career_assessment(profile, role, analysis, None)

    partial_strength = next(
        item for item in result.demonstrated_strengths if item.title == "Solution Roadmaps"
    )
    partial_alignment = next(
        item
        for item in result.target_alignments
        if item.target_requirement == "Product Vision Ownership"
    )
    assert partial_strength.alignment_type is TargetAlignmentType.PARTIALLY_ALIGNED
    assert partial_alignment.alignment_type is TargetAlignmentType.PARTIALLY_ALIGNED
    assert partial_alignment.what_candidate_has
    assert partial_alignment.what_is_still_missing
    assert result.accessibility is CandidateAccessibility.NEAR_TERM_TARGET


def test_no_confirmed_match_never_becomes_a_demonstrated_strength() -> None:
    profile, role, analysis = build_scenario(SCENARIOS[1])
    unsupported_requirement_ids = {
        item.requirement_id
        for item in role.requirement_comparisons
        if item.match_type is MatchType.NO_CONFIRMED_MATCH
    }

    result = synthesize_career_assessment(profile, role, analysis, None)

    assert all(
        comparison_id
        not in {
            comparison.comparison_id
            for comparison in role.requirement_comparisons
            if comparison.requirement_id in unsupported_requirement_ids
        }
        for strength in result.demonstrated_strengths
        for comparison_id in strength.supporting_comparison_ids
    )


def test_strengths_remain_visible_when_direct_match_count_is_zero() -> None:
    profile, role, analysis = build_scenario(SCENARIOS[0])
    no_direct_role = role.model_copy(
        update={
            "requirement_comparisons": [
                item.model_copy(
                    update={
                        "match_type": (
                            MatchType.PARTIAL_MATCH
                            if item.match_type is MatchType.DIRECT_MATCH
                            else item.match_type
                        ),
                        "remaining_difference": (
                            item.remaining_difference
                            or "Direct target-role responsibility remains incomplete."
                        ),
                    }
                )
                for item in role.requirement_comparisons
            ]
        }
    )

    result = synthesize_career_assessment(profile, no_direct_role, analysis, None)

    assert result.direct_match_count == 0
    assert result.demonstrated_strengths
    assert any(
        item.alignment_type is TargetAlignmentType.PARTIALLY_ALIGNED
        for item in result.demonstrated_strengths
    )


def test_employment_title_is_supporting_evidence_not_a_standalone_strength() -> None:
    profile, role, analysis = build_scenario(SCENARIOS[0])
    first = profile.evidence_items[0]
    role_title_evidence = first.model_copy(
        update={
            "capability": profile.current_role,
            "evidence_type": "employment",
            "source_reference": f"{profile.current_role}, current role",
        }
    )
    title_profile = profile.model_copy(
        update={"evidence_items": [role_title_evidence, *profile.evidence_items[1:]]}
    )

    result = synthesize_career_assessment(title_profile, role, analysis, None)

    assert profile.current_role not in {item.title for item in result.demonstrated_strengths}


def test_gap_titles_and_requirement_lists_use_actual_requirement_semantics() -> None:
    profile, role, analysis = build_scenario(SCENARIOS[1])

    result = synthesize_career_assessment(profile, role, analysis, None)

    group = result.grouped_gaps[0]
    generic_titles = {
        "Strategic responsibility",
        "Scope",
        "Functional responsibility",
        "Technical depth",
        "People management scope",
    }
    assert group.display_title not in generic_titles
    assert set(group.underlying_requirement_names) == {
        "Team Coaching",
        "Hiring Ownership",
        "Performance Management",
    }
    assert any(
        requirement.casefold().split()[0] in group.display_title.casefold()
        for requirement in group.underlying_requirement_names
    )


def _gateway(payload: dict[str, object]) -> ModelGateway:
    return ModelGateway(
        provider=FakeModelProvider(outcomes=[json.dumps(payload)]),
        models={ModelRole.REASONING: "fake-synthesis"},
        timeout_seconds=10,
        max_retries=0,
        sleeper=lambda _: None,
    )


def test_model_may_group_but_cannot_set_policy_fields() -> None:
    profile, role, analysis = build_scenario(SCENARIOS[1])
    gap_ids = [str(item.gap_id) for item in role.gaps]
    payload = {
        "strongest_advantages": [],
        "transferable_strengths": [],
        "grouped_gaps": [
            {
                "title": "People leadership ownership",
                "explanation": "The related people-management responsibilities remain distinct.",
                "underlying_gap_ids": gap_ids,
                "what_candidate_already_has": "Confirmed software-delivery evidence.",
                "what_is_missing": "Direct ownership of formal people-management duties.",
                "evidence_to_build": "Verified examples linked to the stated requirements.",
            }
        ],
        "assessment_summary": "Strong delivery evidence with a material ownership difference.",
        "limitations": [],
    }

    result = synthesize_career_assessment(profile, role, analysis, _gateway(payload))

    assert result.status is CareerSynthesisStatus.SUCCEEDED
    assert result.provider == "mock"
    assert result.grouped_gaps[0].severity is GapSeverity.HIGH
    assert result.grouped_gaps[0].requirement_frequency is RequirementFrequency.COMMON
    assert set(result.grouped_gaps[0].underlying_gap_ids) == {item.gap_id for item in role.gaps}


def test_unknown_model_gap_id_fails_closed_to_validated_grouping() -> None:
    profile, role, analysis = build_scenario(SCENARIOS[0])
    payload = {
        "strongest_advantages": [],
        "transferable_strengths": [],
        "grouped_gaps": [
            {
                "title": "Invented gap",
                "explanation": "Unsupported.",
                "underlying_gap_ids": [str(uuid4())],
                "what_candidate_already_has": "Unknown.",
                "what_is_missing": "Unknown.",
                "evidence_to_build": "Unknown.",
            }
        ],
        "assessment_summary": "Unsupported synthesis.",
        "limitations": [],
    }

    result = synthesize_career_assessment(profile, role, analysis, _gateway(payload))

    assert result.status is CareerSynthesisStatus.SUCCEEDED_WITH_FALLBACK
    assert set(result.source_gap_ids) == {item.gap_id for item in role.gaps}
    assert result.provider is None
    assert any("deterministic grouping" in item for item in result.limitations)


def test_fallback_bounds_verbose_validated_source_text() -> None:
    """Provider rejection must not make the deterministic fallback fail validation."""
    profile, role, analysis = build_scenario(SCENARIOS[0])
    verbose = "Grounded but excessively verbose supporting explanation. " * 30
    comparisons = [
        item.model_copy(update={"explanation": verbose}) for item in role.requirement_comparisons
    ]
    gaps = [
        item.model_copy(
            update={
                "remaining_difference": verbose,
                "evidence_needed": verbose,
            }
        )
        for item in role.gaps
    ]
    verbose_role = role.model_copy(update={"requirement_comparisons": comparisons, "gaps": gaps})

    result = synthesize_career_assessment(profile, verbose_role, analysis, None)

    assert result.status is CareerSynthesisStatus.SUCCEEDED_WITH_FALLBACK
    assert all(len(item.explanation) <= 500 for item in result.strongest_advantages)
    assert all(len(item.explanation) <= 500 for item in result.transferable_strengths)
    assert all(len(item.explanation) <= 600 for item in result.grouped_gaps)
    assert all(len(item.what_is_missing) <= 500 for item in result.grouped_gaps)
    assert all(len(item.evidence_to_build) <= 500 for item in result.grouped_gaps)


def test_three_related_high_gaps_are_one_independent_dimension() -> None:
    scenario = SynthesisScenario(
        "related_people_scope",
        "Senior Specialist",
        "Team Lead",
        (
            Finding("System Delivery", "System Delivery", MatchType.DIRECT_MATCH),
            Finding("Quality Ownership", "Quality Ownership", MatchType.DIRECT_MATCH),
            Finding("Reliability", "Reliability", MatchType.DIRECT_MATCH),
            Finding("Stakeholder Alignment", "Stakeholder Alignment", MatchType.DIRECT_MATCH),
            Finding("Technical Design", "Technical Design", MatchType.DIRECT_MATCH),
            Finding(
                "Team Coaching",
                None,
                MatchType.NO_CONFIRMED_MATCH,
                GapCategory.LEADERSHIP_SCOPE,
                GapSeverity.HIGH,
                RequirementCategory.LEADERSHIP,
            ),
            Finding(
                "Hiring",
                None,
                MatchType.NO_CONFIRMED_MATCH,
                GapCategory.LEADERSHIP_SCOPE,
                GapSeverity.HIGH,
                RequirementCategory.LEADERSHIP,
            ),
            Finding(
                "Performance Management",
                None,
                MatchType.NO_CONFIRMED_MATCH,
                GapCategory.LEADERSHIP_SCOPE,
                GapSeverity.HIGH,
                RequirementCategory.LEADERSHIP,
            ),
        ),
        frozenset({CandidateAccessibility.NEAR_TERM_TARGET}),
    )
    profile, role, analysis = build_scenario(scenario)

    result = synthesize_career_assessment(profile, role, analysis, None)

    assert result.raw_high_gap_count == 3
    assert result.independent_severe_dimensions == [CareerGapDimension.PEOPLE_LEADERSHIP]
    assert result.accessibility is CandidateAccessibility.NEAR_TERM_TARGET


def test_small_canonical_sample_with_one_maturity_dimension_is_not_aspirational() -> None:
    scenario = SynthesisScenario(
        "small_ai_sample",
        "Developer",
        "AI Engineer",
        (
            Finding("Python", "Python", MatchType.DIRECT_MATCH),
            Finding("AI Integration", "API Integration", MatchType.TRANSFERABLE_MATCH),
            Finding(
                "Production AI Delivery",
                "AI Project Delivery",
                MatchType.PARTIAL_MATCH,
                GapCategory.EXPERIENCE,
                GapSeverity.HIGH,
                RequirementCategory.TECHNICAL,
            ),
        ),
        frozenset({CandidateAccessibility.NEAR_TERM_TARGET}),
    )
    profile, role, analysis = build_scenario(scenario)
    partial = role.requirement_comparisons[-1].model_copy(
        update={
            "partial_match_subtype": PartialMatchSubtype.CAPABILITY_PRESENT_MATURITY_GAP,
            "maturity_alignment": MaturityAlignment.BELOW_TARGET,
            "production_context_difference": ProductionContextDifference.PROJECT_TO_PRODUCTION,
        }
    )
    role = role.model_copy(
        update={"requirement_comparisons": [*role.requirement_comparisons[:-1], partial]}
    )

    result = synthesize_career_assessment(profile, role, analysis, None)

    assert result.partial_capability_present_count == 1
    assert result.independent_severe_dimensions == [CareerGapDimension.MATURITY]
    assert result.accessibility is CandidateAccessibility.NEAR_TERM_TARGET


def test_independent_high_dimensions_can_justify_aspirational() -> None:
    profile, role, analysis = build_scenario(SCENARIOS[2])

    result = synthesize_career_assessment(profile, role, analysis, None)

    assert len(result.independent_severe_dimensions) == 3
    assert result.accessibility is CandidateAccessibility.ASPIRATIONAL


def test_related_title_evidence_cannot_drive_apply_now() -> None:
    profile, role, analysis = build_scenario(SCENARIOS[4])
    related_role = role.model_copy(
        update={
            "requirement_comparisons": [
                item.model_copy(update={"comparison_scope": ComparisonScope.RELATED_TITLE})
                for item in role.requirement_comparisons
            ],
            "gaps": [
                item.model_copy(update={"comparison_scope": ComparisonScope.RELATED_TITLE})
                for item in role.gaps
            ],
        }
    )

    result = synthesize_career_assessment(profile, related_role, analysis, None)

    assert result.accessibility is CandidateAccessibility.INSUFFICIENT_CANDIDATE_EVIDENCE


def test_transferable_evidence_has_less_policy_weight_than_direct_evidence() -> None:
    profile, role, analysis = build_scenario(SCENARIOS[4])
    evidence_backed = [item for item in role.requirement_comparisons if item.evidence_ids]
    direct_role = role.model_copy(
        update={
            "requirement_comparisons": [
                item.model_copy(update={"match_type": MatchType.DIRECT_MATCH})
                for item in evidence_backed
            ],
            "gaps": [],
        }
    )
    transferable_role = direct_role.model_copy(
        update={
            "requirement_comparisons": [
                item.model_copy(update={"match_type": MatchType.TRANSFERABLE_MATCH})
                for item in direct_role.requirement_comparisons
            ]
        }
    )

    direct = synthesize_career_assessment(profile, direct_role, analysis, None)
    transferable = synthesize_career_assessment(profile, transferable_role, analysis, None)

    assert direct.accessibility is CandidateAccessibility.APPLY_NOW
    assert transferable.accessibility is CandidateAccessibility.NEAR_TERM_TARGET


def test_low_confidence_caps_an_otherwise_apply_now_result() -> None:
    profile, role, analysis = build_scenario(SCENARIOS[4])
    direct_role = role.model_copy(
        update={
            "requirement_comparisons": [
                item.model_copy(
                    update={
                        "match_type": MatchType.DIRECT_MATCH,
                        "confidence": ConfidenceLevel.LOW,
                    }
                )
                for item in role.requirement_comparisons
            ],
            "gaps": [],
            "confidence": ConfidenceLevel.LOW,
        }
    )

    result = synthesize_career_assessment(profile, direct_role, analysis, None)

    assert result.accessibility is CandidateAccessibility.NEAR_TERM_TARGET


def test_maturity_shortfall_remains_partial_and_groups_as_maturity() -> None:
    profile, role, analysis = build_scenario(SCENARIOS[4])
    comparison = role.requirement_comparisons[0]

    result = synthesize_career_assessment(profile, role, analysis, None)

    assert comparison.match_type is MatchType.PARTIAL_MATCH
    assert comparison.candidate_maturity is EvidenceMaturity.DEMONSTRATED
    assert comparison.target_maturity is EvidenceMaturity.PRODUCTION
    assert result.grouped_gaps[0].primary_dimension is CareerGapDimension.MATURITY


def test_technical_maturity_gap_is_not_misclassified_as_ownership() -> None:
    profile, role, analysis = build_scenario(SCENARIOS[3])

    result = synthesize_career_assessment(profile, role, analysis, None)

    assert result.grouped_gaps[0].primary_dimension is CareerGapDimension.MATURITY
    assert CareerGapDimension.TECHNICAL_DEPTH in result.grouped_gaps[0].affected_dimensions
    assert CareerGapDimension.OWNERSHIP not in result.grouped_gaps[0].affected_dimensions


def test_rationale_reports_grouped_burden_without_raw_ids() -> None:
    profile, role, analysis = build_scenario(SCENARIOS[1])

    result = synthesize_career_assessment(profile, role, analysis, None)
    group = result.grouped_gaps[0]

    assert group.underlying_gap_count == 3
    assert group.high_or_blocking_gap_count == 2
    assert group.mandatory_requirement_count == 3
    assert group.preferred_requirement_count == 0
    assert "1 major remaining dimension" in result.accessibility_rationale
    assert "2 high or blocking gaps" in result.accessibility_rationale
    assert "2 mandatory requirements" in result.accessibility_rationale
    assert all(str(gap.gap_id) not in result.accessibility_rationale for gap in role.gaps)
