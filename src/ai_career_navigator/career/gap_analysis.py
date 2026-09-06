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


def _category(requirement: RoleRequirement, comparison: RequirementComparison) -> GapCategory:
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
) -> ConfidenceLevel:
    if accessibility is CandidateAccessibility.INSUFFICIENT_CANDIDATE_EVIDENCE:
        return ConfidenceLevel.INSUFFICIENT
    insufficient = sum(item.confidence is ConfidenceLevel.INSUFFICIENT for item in comparisons)
    if snapshot.evidence_confidence is ConfidenceLevel.INSUFFICIENT or insufficient * 3 >= len(
        comparisons
    ):
        return ConfidenceLevel.LOW
    if snapshot.evidence_confidence is not ConfidenceLevel.HIGH or any(
        item.confidence is not ConfidenceLevel.HIGH for item in comparisons
    ):
        return ConfidenceLevel.MODERATE
    return ConfidenceLevel.HIGH


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
            and comparison.match_type is MatchType.NO_CONFIRMED_MATCH
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
        target = _gap_target(requirement, representative)
        category = _category(requirement, representative)
        evidence_needed, possible_action = _action(category, target)
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
                evidence_needed=evidence_needed,
                possible_action=possible_action,
                confidence=representative.confidence,
            )
        )

    exact_comparisons = [item for item in usable if item.comparison_scope in PRIMARY_TARGET_SCOPES]
    accessibility = classify_accessibility(
        AccessibilityInputs(
            exact_comparison_count=len(exact_comparisons),
            exact_supported_count=sum(
                item.match_type in {MatchType.DIRECT_MATCH, MatchType.TRANSFERABLE_MATCH}
                for item in exact_comparisons
            ),
            exact_high_gap_count=sum(
                item.comparison_scope in PRIMARY_TARGET_SCOPES and item.severity is GapSeverity.HIGH
                for item in gaps
            ),
            exact_moderate_gap_count=sum(
                item.comparison_scope in PRIMARY_TARGET_SCOPES
                and item.severity is GapSeverity.MODERATE
                for item in gaps
            ),
            blocking_gap_count=sum(item.hard_blocker for item in gaps),
            insufficient_comparison_count=sum(
                item.confidence is ConfidenceLevel.INSUFFICIENT for item in usable
            ),
            total_comparison_count=len(usable),
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
    confidence = (
        _assessment_confidence(snapshot, usable, accessibility)
        if usable
        else ConfidenceLevel.INSUFFICIENT
    )
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
    limitations = []
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
