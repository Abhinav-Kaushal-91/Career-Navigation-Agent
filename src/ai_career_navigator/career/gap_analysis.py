"""Deterministic gap generation and candidate accessibility assessment."""

import logging
from collections import defaultdict

from ai_career_navigator.domain import (
    CandidateAccessibility,
    CandidateProfile,
    CareerGoal,
    ComparisonScope,
    ConfidenceLevel,
    CurrentMarketSnapshot,
    GapCategory,
    GapItem,
    GapSeverity,
    MatchType,
    MaturityAlignment,
    OwnershipAlignment,
    PartialMatchSubtype,
    ProductionContextDifference,
    RequirementCategory,
    RequirementComparison,
    RequirementFrequency,
    RoleAssessment,
    RoleRequirement,
    ScopeAlignment,
)
from ai_career_navigator.market import MarketRequirementAnalysis

from .comparison import normalize_capability
from .evidence_coverage import (
    comparison_is_resolved,
    is_hiring_expectation,
    readiness_coverage_issue,
    readiness_coverage_notes,
)
from .gap_policy import (
    AccessibilityInputs,
    classify_accessibility,
    frequency_band,
    gap_severity,
    is_hard_blocker,
)
from .gap_schemas import GapAnalysisResult, GapAnalysisStatus

logger = logging.getLogger(__name__)
PRIMARY_TARGET_SCOPES = {
    ComparisonScope.EXACT_TARGET,
    ComparisonScope.TARGET_VARIANT,
}
_CONFIDENCE_RANK = {
    ConfidenceLevel.INSUFFICIENT: 0,
    ConfidenceLevel.LOW: 1,
    ConfidenceLevel.MODERATE: 2,
    ConfidenceLevel.HIGH: 3,
}


def _category(requirement: RoleRequirement, comparison: RequirementComparison) -> GapCategory:
    if comparison.match_type is None or (
        comparison.match_type is MatchType.NO_CONFIRMED_MATCH
        and comparison.evidence_status not in {"CONFIRMED_UNMET", "CONTRADICTED"}
    ):
        return GapCategory.EVIDENCE
    if comparison.partial_match_subtype is PartialMatchSubtype.CAPABILITY_PRESENT_MATURITY_GAP:
        return GapCategory.EXPERIENCE
    if comparison.partial_match_subtype is PartialMatchSubtype.OWNERSHIP_OR_SCOPE_GAP:
        return GapCategory.LEADERSHIP_SCOPE
    text = f"{requirement.requirement_text} {comparison.remaining_difference or ''}".casefold()
    if requirement.category in {
        RequirementCategory.CREDENTIAL,
        RequirementCategory.EDUCATION,
        RequirementCategory.WORK_AUTHORIZATION,
        RequirementCategory.LANGUAGE,
        RequirementCategory.LOCATION,
    }:
        return GapCategory.CREDENTIAL_PREREQUISITE
    if requirement.category in {RequirementCategory.LEADERSHIP, RequirementCategory.SCOPE} or any(
        term in text
        for term in ("leadership", "architecture ownership", "decision authority", "mentoring")
    ):
        return GapCategory.LEADERSHIP_SCOPE
    if requirement.category in {RequirementCategory.EXPERIENCE, RequirementCategory.DOMAIN} or any(
        term in text for term in ("years", "production", "delivery experience", "industry")
    ):
        return GapCategory.EXPERIENCE
    if comparison.match_type is MatchType.TRANSFERABLE_MATCH:
        return GapCategory.EVIDENCE
    if comparison.match_type is None:
        return GapCategory.EVIDENCE
    return GapCategory.SKILL


def _has_concrete_residual(comparison: RequirementComparison) -> bool:
    if comparison.match_type is not MatchType.TRANSFERABLE_MATCH:
        return True
    return bool(
        comparison.ownership_alignment in {OwnershipAlignment.PARTIAL, OwnershipAlignment.MISSING}
        or comparison.scope_alignment in {ScopeAlignment.PARTIAL, ScopeAlignment.MISSING}
        or comparison.maturity_alignment is MaturityAlignment.BELOW_TARGET
        or comparison.production_context_difference
        in {
            ProductionContextDifference.PROJECT_TO_PRODUCTION,
            ProductionContextDifference.LIMITED_PRODUCTION_DEPTH,
            ProductionContextDifference.OTHER,
        }
    )


def _gap_target(requirement: RoleRequirement, comparison: RequirementComparison) -> str:
    capability = requirement.normalized_capability or requirement.requirement_text
    if comparison.partial_match_subtype is PartialMatchSubtype.CAPABILITY_PRESENT_MATURITY_GAP:
        if comparison.production_context_difference in {
            ProductionContextDifference.PROJECT_TO_PRODUCTION,
            ProductionContextDifference.LIMITED_PRODUCTION_DEPTH,
        }:
            return f"Professional production maturity for {capability}"
        return f"Required maturity for {capability}"
    if comparison.partial_match_subtype is PartialMatchSubtype.OWNERSHIP_OR_SCOPE_GAP:
        return f"Ownership and scope for {capability}"
    return capability


def _frequency(
    requirement_ids: list[object],
    scope: ComparisonScope,
    analysis: MarketRequirementAnalysis,
) -> RequirementFrequency:
    identifiers = set(requirement_ids)
    aggregates = [
        item for item in analysis.summary.requirements if identifiers & set(item.requirement_ids)
    ]
    if not aggregates:
        return RequirementFrequency.INSUFFICIENT_EVIDENCE
    if scope is ComparisonScope.EXACT_TARGET:
        values = [
            item.exact_title_frequency
            for item in aggregates
            if item.exact_title_frequency is not None
        ]
    elif scope is ComparisonScope.TARGET_VARIANT:
        values = [
            item.exact_and_variant_frequency
            for item in aggregates
            if item.exact_and_variant_frequency is not None
        ]
    else:
        denominator = analysis.summary.related_title_analyzed_count
        values = [
            item.related_title_occurrence_count / denominator for item in aggregates if denominator
        ]
    return frequency_band(max(values)) if values else RequirementFrequency.INSUFFICIENT_EVIDENCE


def _action(category: GapCategory, target: str) -> tuple[str, str]:
    actions = {
        GapCategory.SKILL: (
            f"Confirmed evidence for {target}",
            f"Build applied {target} capability.",
        ),
        GapCategory.EXPERIENCE: (
            f"Relevant delivery evidence for {target}",
            f"Gain relevant {target} delivery experience.",
        ),
        GapCategory.LEADERSHIP_SCOPE: (
            f"Ownership evidence for {target}",
            "Gain and document the required ownership scope.",
        ),
        GapCategory.EVIDENCE: (
            f"Direct evidence for {target}",
            f"Document direct evidence demonstrating {target}.",
        ),
        GapCategory.CREDENTIAL_PREREQUISITE: (
            f"Confirmed prerequisite for {target}",
            f"Obtain or confirm the required {target} prerequisite.",
        ),
    }
    return actions[category]


def _assessment_confidence(
    snapshot: CurrentMarketSnapshot,
    comparisons: list[RequirementComparison],
    accessibility: CandidateAccessibility,
    *,
    target_profile_confidence: ConfidenceLevel | None = None,
) -> ConfidenceLevel:
    if accessibility is CandidateAccessibility.INSUFFICIENT_CANDIDATE_EVIDENCE:
        return ConfidenceLevel.INSUFFICIENT
    insufficient = sum(item.confidence is ConfidenceLevel.INSUFFICIENT for item in comparisons)
    if snapshot.evidence_confidence is ConfidenceLevel.INSUFFICIENT or insufficient * 3 >= len(
        comparisons
    ):
        confidence = ConfidenceLevel.LOW
    elif snapshot.evidence_confidence is not ConfidenceLevel.HIGH or any(
        item.confidence is not ConfidenceLevel.HIGH for item in comparisons
    ):
        confidence = ConfidenceLevel.MODERATE
    else:
        confidence = ConfidenceLevel.HIGH
    # The broad retrieval sample cannot establish greater certainty than the
    # actual canonical target baseline. This limits confidence, not candidate fit.
    if target_profile_confidence is not None:
        confidence = min(confidence, target_profile_confidence, key=_CONFIDENCE_RANK.__getitem__)
    return confidence


def assess_candidate_accessibility(
    profile: CandidateProfile,
    goal: CareerGoal,
    snapshot: CurrentMarketSnapshot,
    market_analysis: MarketRequirementAnalysis,
    comparisons: list[RequirementComparison],
) -> GapAnalysisResult:
    """Create deduplicated gaps and a qualitative accessibility conclusion."""

    del profile  # profile evidence is already represented by validated comparison references
    requirements = {item.requirement_id: item for item in market_analysis.requirements}
    grouped: dict[tuple[str, str], list[tuple[RequirementComparison, RoleRequirement]]] = (
        defaultdict(list)
    )
    usable = [item for item in comparisons if item.requirement_id in requirements]
    for comparison in usable:
        requirement = requirements[comparison.requirement_id]
        if not is_hiring_expectation(requirement):
            continue  # Preferences and duties may align; they never create hiring gaps.
        key = (
            requirement.category.value,
            normalize_capability(requirement.normalized_capability or requirement.requirement_text),
        )
        grouped[key].append((comparison, requirement))

    gaps: list[GapItem] = []
    for entries in grouped.values():
        non_direct = [
            item
            for item in entries
            if item[0].match_type is not MatchType.DIRECT_MATCH and _has_concrete_residual(item[0])
        ]
        if not non_direct:
            continue
        exact = [
            item for item in non_direct if item[0].comparison_scope is ComparisonScope.EXACT_TARGET
        ]
        variants = [
            item
            for item in non_direct
            if item[0].comparison_scope is ComparisonScope.TARGET_VARIANT
        ]
        selected = exact or variants or non_direct
        representative, requirement = selected[0]
        requirement_ids = [item[1].requirement_id for item in entries]
        source_requirement_ids = list(
            dict.fromkeys(
                source_id
                for comparison, _ in entries
                for source_id in comparison.source_requirement_ids
            )
        )
        scope = (
            ComparisonScope.EXACT_TARGET
            if exact
            else ComparisonScope.TARGET_VARIANT
            if variants
            else ComparisonScope.RELATED_TITLE
        )
        band = _frequency(source_requirement_ids or requirement_ids, scope, market_analysis)
        hard = any(
            is_hard_blocker(item.category, item.mandatory, item.requirement_text)
            and not item.employer_specific
            and comparison.comparison_scope in PRIMARY_TARGET_SCOPES
            and comparison.match_type is MatchType.NO_CONFIRMED_MATCH
            and comparison.evidence_status in {"CONFIRMED_UNMET", "CONTRADICTED"}
            and bool(comparison.grounded_evidence_quotes)
            for comparison, item in selected
        )
        severity = gap_severity(
            match_type=representative.match_type,
            frequency=band,
            mandatory=any(item.mandatory for _, item in selected),
            preferred=all(item.preferred for _, item in selected),
            scope=scope,
            hard_blocker=hard,
            confidence=representative.confidence,
        )
        if requirement.employer_specific and severity in {GapSeverity.HIGH, GapSeverity.BLOCKING}:
            severity = GapSeverity.MODERATE
        target = _gap_target(requirement, representative)
        category = _category(requirement, representative)
        evidence_needed, possible_action = _action(category, target)
        if representative.match_type is None:
            possible_action = representative.clarification_needed or (
                "Retry the unavailable comparison using the retained evidence."
                if representative.evidence_status == "OPERATION_FAILED"
                else f"Confirm the evidence needed for {target}."
            )
        gaps.append(
            GapItem(
                requirement_id=requirement.requirement_id,
                requirement_ids=requirement_ids,
                source_requirement_ids=source_requirement_ids,
                comparison_scope=scope,
                requirement_frequency=band,
                category=category,
                current_evidence_ids=list(
                    dict.fromkeys(eid for comp, _ in entries for eid in comp.evidence_ids)
                ),
                current_maturity=representative.candidate_maturity,
                target_expectation=target,
                remaining_difference=representative.remaining_difference
                or "A material requirement difference remains.",
                severity=severity,
                hard_blocker=hard,
                employer_specific=requirement.employer_specific,
                required_status=(
                    "MANDATORY"
                    if any(item.mandatory for _, item in selected)
                    else "PREFERRED"
                    if all(item.preferred for _, item in selected)
                    else "UNSPECIFIED"
                ),
                evidence_status=representative.evidence_status,
                clarification_needed=representative.clarification_needed,
                evidence_needed=evidence_needed,
                possible_action=possible_action,
                confidence=representative.confidence,
            )
        )

    exact_comparisons = [
        item
        for item in usable
        if item.comparison_scope in PRIMARY_TARGET_SCOPES
        and not requirements[item.requirement_id].employer_specific
        and is_hiring_expectation(requirements[item.requirement_id])
    ]
    coverage_issue = readiness_coverage_issue(market_analysis, usable)
    coverage_notes = readiness_coverage_notes(market_analysis, usable)
    # Unanswered questions are not negative votes. Preserve the original comparisons
    # on the assessment; score resolved evidence only after the coverage gate passes.
    if market_analysis.canonical_profile is not None and not coverage_issue:
        exact_comparisons = [item for item in exact_comparisons if comparison_is_resolved(item)]
    accessibility = classify_accessibility(
        AccessibilityInputs(
            exact_comparison_count=len(exact_comparisons),
            exact_supported_count=sum(
                item.match_type in {MatchType.DIRECT_MATCH, MatchType.TRANSFERABLE_MATCH}
                for item in exact_comparisons
            ),
            exact_high_gap_count=sum(
                item.comparison_scope in PRIMARY_TARGET_SCOPES
                and item.severity is GapSeverity.HIGH
                and not item.employer_specific
                for item in gaps
            ),
            exact_moderate_gap_count=sum(
                item.comparison_scope in PRIMARY_TARGET_SCOPES
                and item.severity is GapSeverity.MODERATE
                and not item.employer_specific
                for item in gaps
            ),
            blocking_gap_count=sum(item.hard_blocker for item in gaps),
            insufficient_comparison_count=sum(
                item.confidence is ConfidenceLevel.INSUFFICIENT for item in exact_comparisons
            ),
            total_comparison_count=len(exact_comparisons),
            partial_capability_present_count=sum(
                item.partial_match_subtype is PartialMatchSubtype.CAPABILITY_PRESENT_MATURITY_GAP
                for item in exact_comparisons
            ),
            partial_ownership_scope_count=sum(
                item.partial_match_subtype is PartialMatchSubtype.OWNERSHIP_OR_SCOPE_GAP
                for item in exact_comparisons
            ),
            exact_no_match_count=sum(
                item.match_type is MatchType.NO_CONFIRMED_MATCH for item in exact_comparisons
            ),
        )
    )
    employer_checks = [
        item
        for item in usable
        if requirements[item.requirement_id].employer_specific
        and is_hiring_expectation(requirements[item.requirement_id])
        and item.match_type not in {MatchType.DIRECT_MATCH, MatchType.TRANSFERABLE_MATCH}
    ]
    if accessibility is CandidateAccessibility.APPLY_NOW and (employer_checks or coverage_notes):
        accessibility = CandidateAccessibility.APPLY_SELECTIVELY
    if coverage_issue:
        accessibility = CandidateAccessibility.INSUFFICIENT_CANDIDATE_EVIDENCE
    confidence = (
        _assessment_confidence(
            snapshot,
            exact_comparisons,
            accessibility,
            target_profile_confidence=(
                market_analysis.canonical_profile.confidence
                if market_analysis.canonical_profile is not None
                else None
            ),
        )
        if exact_comparisons
        else ConfidenceLevel.INSUFFICIENT
    )
    if coverage_notes and confidence is ConfidenceLevel.HIGH:
        confidence = ConfidenceLevel.MODERATE
    material = sum(item.severity in {GapSeverity.HIGH, GapSeverity.BLOCKING} for item in gaps)
    supported = sum(
        item.match_type in {MatchType.DIRECT_MATCH, MatchType.TRANSFERABLE_MATCH}
        for item in exact_comparisons
    )
    explanation = (
        f"Confirmed evidence supports {supported} "
        f"of {len(exact_comparisons)} exact-target requirements; {material} material gap(s) remain."
        if exact_comparisons
        else "Exact-target comparison evidence is insufficient for a responsible "
        "accessibility assessment."
    )
    limitations = list(coverage_notes)
    if coverage_notes:
        explanation += " " + " ".join(coverage_notes)
    if coverage_issue:
        explanation = coverage_issue
        limitations.append(coverage_issue)
    if accessibility is CandidateAccessibility.INSUFFICIENT_CANDIDATE_EVIDENCE:
        limitations.append("Candidate or exact-target comparison evidence is insufficient.")
    role = RoleAssessment(
        target_role=goal.target_role or snapshot.target_role,
        requirement_comparisons=usable,
        gaps=gaps,
        candidate_accessibility=accessibility,
        explanation=explanation,
        confidence=confidence,
        source_ids=snapshot.source_ids,
    )
    status = GapAnalysisStatus.INSUFFICIENT if limitations else GapAnalysisStatus.SUCCEEDED
    logger.info(
        "gap_analysis_completed comparison_count=%d gap_count=%d blocker_count=%d "
        "accessibility=%s confidence=%s",
        len(usable),
        len(gaps),
        sum(item.hard_blocker for item in gaps),
        accessibility,
        confidence,
    )
    return GapAnalysisResult(status=status, role_assessment=role, limitations=limitations)
