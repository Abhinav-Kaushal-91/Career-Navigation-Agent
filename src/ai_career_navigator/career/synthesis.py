"""Generic grounded synthesis from comparisons and raw gaps to a career assessment."""

import re

from ai_career_navigator.domain import (
    CandidateAccessibility,
    CandidateProfile,
    ComparisonScope,
    ConfidenceLevel,
    EvidenceMaturity,
    FunctionalOverlap,
    GapCategory,
    GapItem,
    GapSeverity,
    MatchType,
    MaturityAlignment,
    OwnershipAlignment,
    PartialMatchSubtype,
    ProductionContextDifference,
    RequirementCategory,
    RequirementFrequency,
    RoleAssessment,
    ScopeAlignment,
)
from ai_career_navigator.market import MarketRequirementAnalysis
from ai_career_navigator.models import ModelGateway, ModelGatewayError, ModelRole

from .bridge_policy import material_gaps
from .evidence_coverage import (
    comparison_is_resolved,
    is_hiring_expectation,
    readiness_coverage_issue,
    readiness_coverage_notes,
)
from .synthesis_prompts import PROMPT_VERSION, SYSTEM_PROMPT, build_synthesis_prompt
from .synthesis_schemas import (
    AdvantageStrengthType,
    CareerAdvantage,
    CareerAdvantageDraft,
    CareerAssessmentSynthesis,
    CareerGapDimension,
    CareerSynthesisDraft,
    CareerSynthesisStatus,
    DemonstratedStrength,
    GroupedCareerGap,
    GroupedCareerGapDraft,
    TargetAlignment,
    TargetAlignmentType,
    TransferableStrength,
    TransferableStrengthDraft,
)

_SEVERITY_RANK = {
    GapSeverity.INSUFFICIENT_EVIDENCE: 0,
    GapSeverity.LOW: 1,
    GapSeverity.MODERATE: 2,
    GapSeverity.HIGH: 3,
    GapSeverity.BLOCKING: 4,
}
_FREQUENCY_RANK = {
    RequirementFrequency.INSUFFICIENT_EVIDENCE: 0,
    RequirementFrequency.RARE: 1,
    RequirementFrequency.OCCASIONAL: 2,
    RequirementFrequency.FREQUENT: 3,
    RequirementFrequency.COMMON: 4,
}
_PRIMARY_SCOPES = {ComparisonScope.EXACT_TARGET, ComparisonScope.TARGET_VARIANT}
_MATCH_WEIGHTS = {
    MatchType.DIRECT_MATCH: 1.0,
    MatchType.TRANSFERABLE_MATCH: 0.7,
    MatchType.NO_CONFIRMED_MATCH: 0.0,
}
_PARTIAL_WEIGHTS = {
    PartialMatchSubtype.CAPABILITY_PRESENT_MATURITY_GAP: 0.55,
    PartialMatchSubtype.OWNERSHIP_OR_SCOPE_GAP: 0.40,
    PartialMatchSubtype.ADJACENT_CAPABILITY_PARTIAL: 0.30,
    None: 0.30,
}
_MATURITY_RANK = {value: index for index, value in enumerate(EvidenceMaturity)}
_DIMENSION_LABELS = {
    CareerGapDimension.FUNCTION: "Functional responsibility",
    CareerGapDimension.OWNERSHIP: "Ownership",
    CareerGapDimension.SCOPE: "Scope",
    CareerGapDimension.MATURITY: "Maturity / production delivery",
    CareerGapDimension.TECHNICAL_DEPTH: "Technical depth",
    CareerGapDimension.DOMAIN_DEPTH: "Domain depth",
    CareerGapDimension.PEOPLE_LEADERSHIP: "People management scope",
    CareerGapDimension.STRATEGIC_RESPONSIBILITY: "Strategic responsibility",
    CareerGapDimension.LIFECYCLE_RESPONSIBILITY: "Lifecycle responsibility",
    CareerGapDimension.METRICS_OUTCOME_OWNERSHIP: "Metrics and outcome ownership",
    CareerGapDimension.PREREQUISITE: "Prerequisite",
}
_DIMENSION_PRIORITY = (
    CareerGapDimension.PREREQUISITE,
    CareerGapDimension.PEOPLE_LEADERSHIP,
    CareerGapDimension.METRICS_OUTCOME_OWNERSHIP,
    CareerGapDimension.LIFECYCLE_RESPONSIBILITY,
    CareerGapDimension.STRATEGIC_RESPONSIBILITY,
    CareerGapDimension.MATURITY,
    CareerGapDimension.SCOPE,
    CareerGapDimension.TECHNICAL_DEPTH,
    CareerGapDimension.DOMAIN_DEPTH,
    CareerGapDimension.OWNERSHIP,
    CareerGapDimension.FUNCTION,
)
_PEOPLE_TERMS = ("hiring", "coaching", "mentoring", "direct report", "performance management")
_METRICS_TERMS = ("metric", "kpi", "outcome", "value realization", "business value")
_LIFECYCLE_TERMS = ("lifecycle", "launch", "adoption", "iteration")
_STRATEGY_TERMS = ("strategy", "strategic", "vision", "roadmap", "priorit")
_SCOPE_TERMS = ("enterprise", "organization-wide", "cross-functional scope", "scale")
_TECHNICAL_TERMS = (
    "software",
    "engineering",
    "machine learning",
    "data science",
    "cloud",
    "architecture",
    "api",
    "automation",
)
_DOMAIN_TERMS = ("domain", "industry", "regulatory", "sector")
_TITLE_STOP_WORDS = {
    "and",
    "for",
    "the",
    "with",
    "role",
    "responsibility",
    "responsibilities",
    "experience",
    "capability",
    "skills",
}
_GENERIC_GAP_TITLES = {value.casefold() for value in _DIMENSION_LABELS.values()}
_CONFIDENCE_RANK = {
    ConfidenceLevel.INSUFFICIENT: 0,
    ConfidenceLevel.LOW: 1,
    ConfidenceLevel.MODERATE: 2,
    ConfidenceLevel.HIGH: 3,
}


class CareerSynthesisValidationError(ValueError):
    """Raised when a model synthesis escapes its supplied source objects."""


def _requirement_maps(analysis: MarketRequirementAnalysis):
    requirements = {item.requirement_id: item for item in analysis.requirements}
    frequencies = {
        requirement_id: aggregate.combined_frequency
        for aggregate in analysis.summary.requirements
        for requirement_id in aggregate.requirement_ids
    }
    return requirements, frequencies


def _payload(
    profile: CandidateProfile,
    role: RoleAssessment,
    analysis: MarketRequirementAnalysis,
) -> dict[str, object]:
    requirements, frequencies = _requirement_maps(analysis)
    comparisons = [
        item for item in role.requirement_comparisons if item.requirement_id in requirements
    ]
    comparison_by_requirement = {item.requirement_id: item for item in comparisons}
    evidence_ids = {evidence_id for item in comparisons for evidence_id in item.evidence_ids} | {
        evidence_id for gap in role.gaps for evidence_id in gap.current_evidence_ids
    }
    approved = {
        item.evidence_id: item
        for item in profile.approved_evidence_items
        if item.evidence_id in evidence_ids
    }
    return {
        "target_role": role.target_role,
        "candidate_summary": {
            "current_role": profile.current_role,
            "career_stage": profile.career_stage.value,
        },
        "comparisons": [
            {
                "comparison_id": str(item.comparison_id),
                "requirement_id": str(item.requirement_id),
                "requirement_name": requirements[item.requirement_id].normalized_capability
                or requirements[item.requirement_id].requirement_text,
                "requirement_category": requirements[item.requirement_id].category.value,
                "statement_type": requirements[item.requirement_id].statement_type.value,
                "employer_specific": requirements[item.requirement_id].employer_specific,
                "preferred": requirements[item.requirement_id].preferred,
                "requirement_frequency": frequencies.get(item.requirement_id),
                "match_type": item.match_type.value if item.match_type else "INSUFFICIENT",
                "candidate_maturity": (
                    item.candidate_maturity.value if item.candidate_maturity else None
                ),
                "target_maturity": item.target_maturity.value if item.target_maturity else None,
                "functional_overlap": item.functional_overlap.value,
                "ownership_alignment": item.ownership_alignment.value,
                "scope_alignment": item.scope_alignment.value,
                "maturity_alignment": item.maturity_alignment.value,
                "production_context_difference": item.production_context_difference.value,
                "outcome_alignment": item.outcome_alignment.value,
                "evidence_status": item.evidence_status,
                "clarification_needed": item.clarification_needed,
                "matched_alternative": item.matched_alternative,
                "partial_match_subtype": (
                    item.partial_match_subtype.value if item.partial_match_subtype else None
                ),
                "transferable_capability": item.transferable_capability,
                "remaining_difference": item.remaining_difference,
                "confidence": item.confidence.value,
                "supporting_evidence_ids": [str(value) for value in item.evidence_ids],
            }
            for item in comparisons
        ],
        "evidence": [
            {
                "evidence_id": str(item.evidence_id),
                "capability": item.capability,
                "description": item.description,
                "maturity": item.maturity_level.value,
                "context": item.context,
            }
            for item in approved.values()
        ],
        "gaps": [
            {
                "gap_id": str(item.gap_id),
                "requirement_ids": [str(value) for value in item.requirement_ids],
                "gap_type": item.category.value,
                "dimensions": [
                    value.value
                    for value in _gap_dimensions(item, requirements, comparison_by_requirement)
                ],
                "severity": item.severity.value,
                "evidence_status": item.evidence_status,
                "clarification_needed": item.clarification_needed,
                "requirement_frequency": item.requirement_frequency.value,
                "mandatory": any(
                    requirements[value].mandatory
                    for value in (item.requirement_ids or [item.requirement_id])
                    if value in requirements
                ),
                "preferred": all(
                    requirements[value].preferred
                    for value in (item.requirement_ids or [item.requirement_id])
                    if value in requirements
                ),
                "target_expectation": item.target_expectation,
                "remaining_difference": item.remaining_difference,
                "current_evidence_ids": [str(value) for value in item.current_evidence_ids],
                "evidence_needed": item.evidence_needed,
            }
            for item in material_gaps(role.gaps)
        ],
    }


def _gap_dimensions(
    gap: GapItem,
    requirements: dict[object, object],
    comparisons: dict[object, object],
) -> tuple[CareerGapDimension, ...]:
    """Classify from structured facts and requirement semantics, not generic gap prose."""

    requirement_ids = gap.requirement_ids or [gap.requirement_id]
    categories = {
        requirement.category
        for requirement_id in requirement_ids
        if (requirement := requirements.get(requirement_id)) is not None
    }
    related_comparisons = [
        comparison
        for requirement_id in requirement_ids
        if (comparison := comparisons.get(requirement_id)) is not None
    ]
    text = gap.target_expectation.casefold()
    dimensions: set[CareerGapDimension] = set()
    if any(
        comparison.functional_overlap in {FunctionalOverlap.LOW, FunctionalOverlap.NONE}
        for comparison in related_comparisons
    ):
        dimensions.add(CareerGapDimension.FUNCTION)
    if any(
        comparison.ownership_alignment in {OwnershipAlignment.PARTIAL, OwnershipAlignment.MISSING}
        for comparison in related_comparisons
    ):
        dimensions.add(CareerGapDimension.OWNERSHIP)
    if any(
        comparison.scope_alignment in {ScopeAlignment.PARTIAL, ScopeAlignment.MISSING}
        for comparison in related_comparisons
    ):
        dimensions.add(CareerGapDimension.SCOPE)
    if any(
        comparison.maturity_alignment is MaturityAlignment.BELOW_TARGET
        or comparison.production_context_difference
        in {
            ProductionContextDifference.PROJECT_TO_PRODUCTION,
            ProductionContextDifference.LIMITED_PRODUCTION_DEPTH,
        }
        for comparison in related_comparisons
    ):
        dimensions.add(CareerGapDimension.MATURITY)
    if gap.category is GapCategory.CREDENTIAL_PREREQUISITE or categories & {
        RequirementCategory.CREDENTIAL,
        RequirementCategory.EDUCATION,
        RequirementCategory.WORK_AUTHORIZATION,
        RequirementCategory.LANGUAGE,
    }:
        dimensions.add(CareerGapDimension.PREREQUISITE)
    if any(term in text for term in _PEOPLE_TERMS):
        dimensions.add(CareerGapDimension.PEOPLE_LEADERSHIP)
    if any(term in text for term in _METRICS_TERMS):
        dimensions.add(CareerGapDimension.METRICS_OUTCOME_OWNERSHIP)
    if any(term in text for term in _LIFECYCLE_TERMS):
        dimensions.add(CareerGapDimension.LIFECYCLE_RESPONSIBILITY)
    if any(term in text for term in _STRATEGY_TERMS):
        dimensions.add(CareerGapDimension.STRATEGIC_RESPONSIBILITY)
    if any(term in text for term in _SCOPE_TERMS):
        dimensions.add(CareerGapDimension.SCOPE)
    if any(term in text for term in _TECHNICAL_TERMS):
        dimensions.add(CareerGapDimension.TECHNICAL_DEPTH)
    if any(term in text for term in _DOMAIN_TERMS) or RequirementCategory.DOMAIN in categories:
        dimensions.add(CareerGapDimension.DOMAIN_DEPTH)
    if any(term in text for term in ("ownership", "accountability", "decision authority")):
        dimensions.add(CareerGapDimension.OWNERSHIP)
    if (
        any(
            comparison.candidate_maturity is not None
            and comparison.target_maturity is not None
            and _MATURITY_RANK[comparison.candidate_maturity]
            < _MATURITY_RANK[comparison.target_maturity]
            for comparison in related_comparisons
        )
        or "production" in text
    ):
        dimensions.add(CareerGapDimension.MATURITY)
    if gap.category is GapCategory.LEADERSHIP_SCOPE:
        dimensions.add(CareerGapDimension.SCOPE)
    if RequirementCategory.LEADERSHIP in categories:
        dimensions.add(CareerGapDimension.PEOPLE_LEADERSHIP)
    if RequirementCategory.SCOPE in categories:
        dimensions.add(CareerGapDimension.SCOPE)
    if RequirementCategory.TECHNICAL in categories or gap.category is GapCategory.SKILL:
        dimensions.add(CareerGapDimension.TECHNICAL_DEPTH)
    if not dimensions:
        dimensions.add(CareerGapDimension.FUNCTION)
    return tuple(item for item in _DIMENSION_PRIORITY if item in dimensions)


def _primary_dimension(dimensions: tuple[CareerGapDimension, ...]) -> CareerGapDimension:
    return dimensions[0]


def _group_severity(gaps: list[GapItem]) -> GapSeverity:
    if any(item.severity is GapSeverity.BLOCKING for item in gaps):
        return GapSeverity.BLOCKING
    if sum(item.severity is GapSeverity.HIGH for item in gaps) >= 2:
        return GapSeverity.HIGH
    return max(gaps, key=lambda item: _SEVERITY_RANK[item.severity]).severity


def _bounded_text(value: str, maximum: int) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= maximum:
        return normalized
    return normalized[: maximum - 1].rstrip() + "…"


def _content_tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.casefold())
        if len(token) > 2 and token not in _TITLE_STOP_WORDS
    }


def _requirement_names(gap: GapItem, requirements: dict[object, object]) -> list[str]:
    names = []
    for requirement_id in gap.requirement_ids or [gap.requirement_id]:
        requirement = requirements.get(requirement_id)
        if requirement is None:
            continue
        name = requirement.normalized_capability or requirement.requirement_text
        if name not in names:
            names.append(name)
    return names or [gap.target_expectation]


def _semantic_family(
    names: list[str],
    gap: GapItem,
    comparisons: dict[object, object] | None = None,
) -> str | None:
    text = " ".join(names).casefold()
    related = [
        comparison
        for requirement_id in (gap.requirement_ids or [gap.requirement_id])
        if comparisons and (comparison := comparisons.get(requirement_id)) is not None
    ]
    if any(
        item.production_context_difference
        in {
            ProductionContextDifference.PROJECT_TO_PRODUCTION,
            ProductionContextDifference.LIMITED_PRODUCTION_DEPTH,
        }
        for item in related
    ):
        return "production-maturity"
    if any(
        item.partial_match_subtype is PartialMatchSubtype.CAPABILITY_PRESENT_MATURITY_GAP
        for item in related
    ):
        return "capability-maturity"
    if any(
        item.partial_match_subtype is PartialMatchSubtype.OWNERSHIP_OR_SCOPE_GAP for item in related
    ):
        return "ownership-scope"
    if gap.category is GapCategory.CREDENTIAL_PREREQUISITE:
        return "prerequisite"
    if any(term in text for term in _PEOPLE_TERMS) or any(
        term in text for term in ("people management", "team management", "team leadership")
    ):
        return "people-management"
    if any(term in text for term in _METRICS_TERMS):
        return "metrics-outcomes"
    if any(term in text for term in _LIFECYCLE_TERMS):
        return "lifecycle"
    if any(term in text for term in _STRATEGY_TERMS):
        return "strategy"
    return None


def _gaps_are_one_theme(
    gaps: list[GapItem],
    requirements: dict[object, object],
    comparisons: dict[object, object] | None = None,
) -> bool:
    if len(gaps) < 2:
        return True
    names_by_gap = [_requirement_names(gap, requirements) for gap in gaps]
    families = [_semantic_family(names, gap, comparisons) for names, gap in zip(names_by_gap, gaps)]
    if families[0] is not None and len(set(families)) == 1:
        return True
    token_sets = [_content_tokens(" ".join(names)) for names in names_by_gap]
    return bool(set.intersection(*token_sets)) if token_sets else False


def _display_gap_title(gaps: list[GapItem], requirements: dict[object, object]) -> str:
    names = list(
        dict.fromkeys(name for gap in gaps for name in _requirement_names(gap, requirements))
    )
    return _bounded_text(" / ".join(names), 120)


def _fallback_gap_groups(
    gaps: list[GapItem],
    requirements: dict[object, object],
    comparisons: dict[object, object] | None = None,
) -> list[list[GapItem]]:
    """Conservatively group only requirements with an explicit shared semantic family."""

    grouped: dict[str, list[GapItem]] = {}
    for gap in gaps:
        names = _requirement_names(gap, requirements)
        family = _semantic_family(names, gap, comparisons)
        key = f"family:{family}" if family else f"gap:{gap.gap_id}"
        grouped.setdefault(key, []).append(gap)
    return list(grouped.values())


def _alignment_type(match_type: MatchType) -> TargetAlignmentType:
    return {
        MatchType.DIRECT_MATCH: TargetAlignmentType.DIRECTLY_ALIGNED,
        MatchType.TRANSFERABLE_MATCH: TargetAlignmentType.TRANSFERABLE,
        MatchType.PARTIAL_MATCH: TargetAlignmentType.PARTIALLY_ALIGNED,
    }[match_type]


def _is_role_title_evidence(item: object) -> bool:
    capability = " ".join(item.capability.casefold().split())
    reference = " ".join(item.source_reference.casefold().split())
    return item.evidence_type.casefold() == "employment" and capability in reference


def _demonstrated_story(
    profile: CandidateProfile,
    role: RoleAssessment,
    analysis: MarketRequirementAnalysis,
) -> tuple[list[DemonstratedStrength], list[TargetAlignment]]:
    requirements, _ = _requirement_maps(analysis)
    approved = {item.evidence_id: item for item in profile.approved_evidence_items}
    usable_matches = {
        MatchType.DIRECT_MATCH,
        MatchType.TRANSFERABLE_MATCH,
        MatchType.PARTIAL_MATCH,
    }
    all_relevant = [
        comparison
        for comparison in role.requirement_comparisons
        if comparison.match_type in usable_matches
        and comparison.requirement_id in requirements
        and any(value in approved for value in comparison.evidence_ids)
    ]
    primary_relevant = [item for item in all_relevant if item.comparison_scope in _PRIMARY_SCOPES]
    relevant = primary_relevant or all_relevant
    by_capability: dict[str, dict[str, object]] = {}
    for comparison in relevant:
        for evidence_id in comparison.evidence_ids:
            evidence = approved.get(evidence_id)
            if (
                evidence is None
                or _is_role_title_evidence(evidence)
                or _MATURITY_RANK[evidence.maturity_level]
                < _MATURITY_RANK[EvidenceMaturity.DEMONSTRATED]
            ):
                continue
            key = " ".join(evidence.capability.casefold().split())
            record = by_capability.setdefault(key, {"evidence": [], "comparisons": []})
            if evidence not in record["evidence"]:
                record["evidence"].append(evidence)
            if comparison not in record["comparisons"]:
                record["comparisons"].append(comparison)

    alignment_rank = {
        MatchType.PARTIAL_MATCH: 1,
        MatchType.TRANSFERABLE_MATCH: 2,
        MatchType.DIRECT_MATCH: 3,
    }

    def rank(record: dict[str, object]) -> tuple[int, int, int, int, int, int]:
        evidence_items = record["evidence"]
        comparisons = record["comparisons"]
        return (
            max(_MATURITY_RANK[item.maturity_level] for item in evidence_items),
            int(any(item.outcome or item.metric for item in evidence_items)),
            sum(item.comparison_scope in _PRIMARY_SCOPES for item in comparisons),
            max(alignment_rank[item.match_type] for item in comparisons),
            len(comparisons),
            min(_CONFIDENCE_RANK[item.confidence] for item in comparisons),
        )

    demonstrated = []
    for record in sorted(by_capability.values(), key=rank, reverse=True)[:8]:
        evidence_items = record["evidence"]
        comparisons = record["comparisons"]
        best_evidence = max(
            evidence_items,
            key=lambda item: (
                _MATURITY_RANK[item.maturity_level],
                bool(item.outcome or item.metric),
                _CONFIDENCE_RANK[item.confidence],
            ),
        )
        best_match = max(comparisons, key=lambda item: alignment_rank[item.match_type]).match_type
        target_names = list(
            dict.fromkeys(
                requirements[item.requirement_id].normalized_capability
                or requirements[item.requirement_id].requirement_text
                for item in comparisons
            )
        )
        summary_parts = [best_evidence.description]
        for value in (best_evidence.outcome, best_evidence.metric):
            if value and value.casefold() not in best_evidence.description.casefold():
                summary_parts.append(value)
        demonstrated.append(
            DemonstratedStrength(
                title=_bounded_text(best_evidence.capability, 100),
                summary=_bounded_text(" ".join(summary_parts), 500),
                alignment_type=_alignment_type(best_match),
                target_requirements=target_names,
                supporting_comparison_ids=[item.comparison_id for item in comparisons],
                supporting_evidence_ids=[item.evidence_id for item in evidence_items],
                maturity=best_evidence.maturity_level,
                confidence=min(
                    [item.confidence for item in evidence_items]
                    + [item.confidence for item in comparisons],
                    key=lambda value: _CONFIDENCE_RANK[value],
                ),
            )
        )

    alignments = []
    for comparison in relevant:
        evidence_items = [approved[value] for value in comparison.evidence_ids if value in approved]
        strong_evidence = [
            item
            for item in evidence_items
            if _MATURITY_RANK[item.maturity_level] >= _MATURITY_RANK[EvidenceMaturity.DEMONSTRATED]
        ]
        if not strong_evidence:
            continue
        capability_evidence = [
            item for item in strong_evidence if not _is_role_title_evidence(item)
        ] or strong_evidence
        capabilities = "; ".join(dict.fromkeys(item.capability for item in capability_evidence))
        requirement = requirements[comparison.requirement_id]
        requirement_name = requirement.normalized_capability or requirement.requirement_text
        evidence_summary = _bounded_text(
            f"Confirmed evidence in {capabilities}: {capability_evidence[0].description}", 500
        )
        alignments.append(
            TargetAlignment(
                candidate_capability=_bounded_text(capabilities, 160),
                target_requirement=_bounded_text(requirement_name, 160),
                alignment_type=_alignment_type(comparison.match_type),
                what_candidate_has=evidence_summary,
                what_is_still_missing=(
                    _bounded_text(
                        comparison.remaining_difference
                        or f"Direct evidence for {requirement_name} remains incomplete.",
                        500,
                    )
                    if comparison.match_type is MatchType.PARTIAL_MATCH
                    else None
                ),
                supporting_comparison_ids=[comparison.comparison_id],
                supporting_evidence_ids=[item.evidence_id for item in strong_evidence],
            )
        )
    return demonstrated, alignments


def _fallback_draft(
    profile: CandidateProfile,
    role: RoleAssessment,
    analysis: MarketRequirementAnalysis,
) -> CareerSynthesisDraft:
    requirements, _ = _requirement_maps(analysis)
    evidence = {item.evidence_id: item for item in profile.approved_evidence_items}
    supported = [
        item
        for item in role.requirement_comparisons
        if item.match_type in {MatchType.DIRECT_MATCH, MatchType.TRANSFERABLE_MATCH}
        and item.evidence_ids
        and item.requirement_id in requirements
    ]
    advantages = []
    for item in supported[:6]:
        name = (
            item.matched_alternative
            or requirements[item.requirement_id].normalized_capability
            or requirements[item.requirement_id].requirement_text
        )
        advantages.append(
            CareerAdvantageDraft(
                title=_bounded_text(name, 100),
                explanation=_bounded_text(
                    item.explanation or "Confirmed evidence supports this requirement.", 500
                ),
                supporting_comparison_ids=[item.comparison_id],
                supporting_evidence_ids=item.evidence_ids,
                strength_type=(
                    AdvantageStrengthType.DIRECT
                    if item.match_type is MatchType.DIRECT_MATCH
                    else AdvantageStrengthType.TRANSFERABLE
                ),
            )
        )
    transfers = []
    for item in supported:
        if item.match_type is not MatchType.TRANSFERABLE_MATCH:
            continue
        source_names = [
            evidence[value].capability for value in item.evidence_ids if value in evidence
        ]
        if not source_names:
            continue
        target = (
            requirements[item.requirement_id].normalized_capability
            or requirements[item.requirement_id].requirement_text
        )
        transfers.append(
            TransferableStrengthDraft(
                source_capability=_bounded_text("; ".join(dict.fromkeys(source_names)), 100),
                target_application=_bounded_text(target, 100),
                explanation=_bounded_text(
                    item.explanation or "Confirmed adjacent experience transfers.", 500
                ),
                supporting_comparison_ids=[item.comparison_id],
                supporting_evidence_ids=item.evidence_ids,
            )
        )
        if len(transfers) == 6:
            break
    gap_drafts = []
    comparison_by_requirement = {item.requirement_id: item for item in role.requirement_comparisons}
    for items in _fallback_gap_groups(
        material_gaps(role.gaps), requirements, comparison_by_requirement
    ):
        existing = [
            evidence[value].capability
            for item in items
            for value in item.current_evidence_ids
            if value in evidence
        ]
        gap_drafts.append(
            GroupedCareerGapDraft(
                title=_display_gap_title(items, requirements),
                explanation=_bounded_text(
                    " ".join(dict.fromkeys(item.remaining_difference for item in items)), 600
                ),
                underlying_gap_ids=[item.gap_id for item in items],
                what_candidate_already_has=_bounded_text(
                    (
                        "; ".join(dict.fromkeys(existing))
                        if existing
                        else "No directly supporting evidence is confirmed."
                    ),
                    500,
                ),
                what_is_missing=_bounded_text(
                    " ".join(dict.fromkeys(item.remaining_difference for item in items)), 500
                ),
                evidence_to_build=_bounded_text(
                    "; ".join(
                        dict.fromkeys(
                            item.evidence_needed or f"Direct evidence of {item.target_expectation}"
                            for item in items
                        )
                    ),
                    500,
                ),
            )
        )
    return CareerSynthesisDraft(
        strongest_advantages=advantages,
        transferable_strengths=transfers,
        grouped_gaps=gap_drafts,
        assessment_summary="The validated candidate evidence and target requirements are ready "
        "for a grounded career-level interpretation.",
        limitations=[],
    )


def _validate_draft(
    draft: CareerSynthesisDraft,
    role: RoleAssessment,
    profile: CandidateProfile,
    analysis: MarketRequirementAnalysis,
) -> None:
    comparisons = {item.comparison_id: item for item in role.requirement_comparisons}
    approved_ids = {item.evidence_id for item in profile.approved_evidence_items}
    material_ids = {item.gap_id for item in material_gaps(role.gaps)}
    gaps_by_id = {item.gap_id: item for item in material_gaps(role.gaps)}
    requirements, _ = _requirement_maps(analysis)

    for advantage in draft.strongest_advantages:
        selected = [comparisons.get(value) for value in advantage.supporting_comparison_ids]
        if any(item is None for item in selected):
            raise CareerSynthesisValidationError("advantage contains an unknown comparison ID")
        if any(
            item.match_type not in {MatchType.DIRECT_MATCH, MatchType.TRANSFERABLE_MATCH}
            for item in selected
            if item is not None
        ):
            raise CareerSynthesisValidationError("advantage uses an unsupported comparison")
        allowed_evidence = {
            value for item in selected if item is not None for value in item.evidence_ids
        }
        if not set(advantage.supporting_evidence_ids).issubset(allowed_evidence & approved_ids):
            raise CareerSynthesisValidationError("advantage contains unsupported evidence")

    for transfer in draft.transferable_strengths:
        selected = [comparisons.get(value) for value in transfer.supporting_comparison_ids]
        if any(item is None for item in selected):
            raise CareerSynthesisValidationError("transfer contains an unknown comparison ID")
        if any(
            item.match_type not in {MatchType.TRANSFERABLE_MATCH, MatchType.PARTIAL_MATCH}
            for item in selected
            if item is not None
        ):
            raise CareerSynthesisValidationError("transfer uses an unsupported comparison")
        allowed_evidence = {
            value for item in selected if item is not None for value in item.evidence_ids
        }
        if not set(transfer.supporting_evidence_ids).issubset(allowed_evidence & approved_ids):
            raise CareerSynthesisValidationError("transfer contains unsupported evidence")

    grouped_ids = [value for group in draft.grouped_gaps for value in group.underlying_gap_ids]
    if len(grouped_ids) != len(set(grouped_ids)) or set(grouped_ids) != material_ids:
        raise CareerSynthesisValidationError(
            "grouped gaps must cover every material gap exactly once"
        )
    for group in draft.grouped_gaps:
        sources = [gaps_by_id[value] for value in group.underlying_gap_ids]
        if not _gaps_are_one_theme(
            sources,
            requirements,
            {item.requirement_id: item for item in role.requirement_comparisons},
        ):
            raise CareerSynthesisValidationError(
                "grouped gaps combine unrelated career-development themes"
            )
        requirement_names = [
            name for gap in sources for name in _requirement_names(gap, requirements)
        ]
        if group.title.casefold() in _GENERIC_GAP_TITLES or not (
            _content_tokens(group.title) & _content_tokens(" ".join(requirement_names))
        ):
            raise CareerSynthesisValidationError(
                "grouped gap title must describe its underlying target requirements"
            )
    if material_ids and re.search(
        r"\b(?:no|zero|0) material gaps?\b", draft.assessment_summary, re.I
    ):
        raise CareerSynthesisValidationError("summary contradicts the grounded material gaps")
    if re.search(
        r"\b(?:apply now|apply selectively|near[- ]term target|aspirational|poor fit|"
        r"limited fit)\b",
        draft.assessment_summary,
        re.I,
    ):
        raise CareerSynthesisValidationError(
            "model summary must not set the deterministic accessibility verdict"
        )


def _accessibility(
    role: RoleAssessment,
    analysis: MarketRequirementAnalysis,
) -> tuple[CandidateAccessibility, dict[str, object]]:
    """Apply a role-neutral policy over primary-scope evidence and independent dimensions."""

    requirements, _ = _requirement_maps(analysis)
    comparison_by_requirement = {item.requirement_id: item for item in role.requirement_comparisons}
    primary = [
        item
        for item in role.requirement_comparisons
        if item.comparison_scope in _PRIMARY_SCOPES
        and item.requirement_id in requirements
        and not requirements[item.requirement_id].employer_specific
        and is_hiring_expectation(requirements[item.requirement_id])
    ]
    employer_specific_checks = sum(
        item.comparison_scope in _PRIMARY_SCOPES
        and item.requirement_id in requirements
        and requirements[item.requirement_id].employer_specific
        and is_hiring_expectation(requirements[item.requirement_id])
        and item.match_type not in {MatchType.DIRECT_MATCH, MatchType.TRANSFERABLE_MATCH}
        for item in role.requirement_comparisons
    )
    counts = {match: sum(item.match_type is match for item in primary) for match in MatchType}
    unresolved_ids = {
        requirement_id
        for gap in role.gaps
        if gap.severity is GapSeverity.INSUFFICIENT_EVIDENCE and gap.clarification_needed
        for requirement_id in (gap.requirement_ids or [gap.requirement_id])
    }
    insufficient = sum(
        item.match_type is None
        or item.confidence is ConfidenceLevel.INSUFFICIENT
        or (item.evidence_status == "UNKNOWN" and bool(item.clarification_needed))
        or item.requirement_id in unresolved_ids
        for item in primary
    )
    primary_gaps = [
        item
        for item in material_gaps(role.gaps)
        if item.comparison_scope in _PRIMARY_SCOPES and not item.employer_specific
    ]
    gap_dimensions = {
        item.gap_id: _gap_dimensions(item, requirements, comparison_by_requirement)
        for item in primary_gaps
    }
    severe_dimensions = tuple(
        dimension
        for dimension in _DIMENSION_PRIORITY
        if any(
            item.severity in {GapSeverity.HIGH, GapSeverity.BLOCKING}
            and _primary_dimension(gap_dimensions[item.gap_id]) is dimension
            for item in primary_gaps
        )
    )
    high_count = sum(item.severity is GapSeverity.HIGH for item in primary_gaps)
    blocking_count = sum(
        item.hard_blocker or item.severity is GapSeverity.BLOCKING for item in primary_gaps
    )
    severe_requirement_ids = {
        requirement_id
        for item in primary_gaps
        if item.severity in {GapSeverity.HIGH, GapSeverity.BLOCKING}
        for requirement_id in (item.requirement_ids or [item.requirement_id])
    }
    mandatory_severe_count = sum(
        bool(requirements[requirement_id].mandatory)
        for requirement_id in severe_requirement_ids
        if requirement_id in requirements
    )
    diagnostics: dict[str, object] = {
        "counts": counts,
        "insufficient_count": insufficient,
        "independent_severe_dimensions": severe_dimensions,
        "raw_high_gap_count": high_count,
        "raw_blocking_gap_count": blocking_count,
        "mandatory_severe_requirement_count": mandatory_severe_count,
        "primary_gap_count": len(primary_gaps),
        "partial_capability_present_count": 0,
        "partial_adjacent_count": 0,
        "partial_ownership_scope_count": 0,
        "employer_specific_checks": employer_specific_checks,
    }
    coverage_issue = readiness_coverage_issue(analysis, role.requirement_comparisons)
    coverage_notes = readiness_coverage_notes(analysis, role.requirement_comparisons)
    diagnostics["coverage_note"] = (
        "Unanswered evidence questions and processing checks remain listed separately; "
        "they are not confirmed capability deficits."
        if coverage_notes else ""
    )
    if coverage_issue:
        diagnostics["confidence_note"] = coverage_issue
        return CandidateAccessibility.INSUFFICIENT_CANDIDATE_EVIDENCE, diagnostics
    if not primary or insufficient * 2 >= len(primary):
        return CandidateAccessibility.INSUFFICIENT_CANDIDATE_EVIDENCE, diagnostics
    if sum(item.confidence is ConfidenceLevel.LOW for item in primary) * 2 >= len(primary):
        diagnostics["confidence_note"] = (
            "Most primary comparisons have low confidence; stronger comparison evidence is "
            "needed before assigning an application recommendation."
        )
        return CandidateAccessibility.INSUFFICIENT_CANDIDATE_EVIDENCE, diagnostics
    if blocking_count:
        return CandidateAccessibility.POOR_FIT, diagnostics

    if analysis.canonical_profile is not None:
        # Missing/failed comparisons remain in provenance and diagnostics, not fit votes.
        primary = [item for item in primary if comparison_is_resolved(item)]
        counts = {match: sum(item.match_type is match for item in primary) for match in MatchType}

    def comparison_weight(item: object) -> float:
        if item.match_type is MatchType.PARTIAL_MATCH:
            return _PARTIAL_WEIGHTS[item.partial_match_subtype]
        return _MATCH_WEIGHTS.get(item.match_type, 0.0)

    weighted_support = sum(comparison_weight(item) for item in primary) / len(primary)
    direct_share = counts[MatchType.DIRECT_MATCH] / len(primary)
    no_match_share = counts[MatchType.NO_CONFIRMED_MATCH] / len(primary)
    moderate_count = sum(item.severity is GapSeverity.MODERATE for item in primary_gaps)
    diagnostics["weighted_support"] = weighted_support
    diagnostics["direct_share"] = direct_share
    partial_capability_present = sum(
        item.partial_match_subtype is PartialMatchSubtype.CAPABILITY_PRESENT_MATURITY_GAP
        for item in primary
    )
    partial_adjacent = sum(
        item.match_type is MatchType.PARTIAL_MATCH
        and item.partial_match_subtype in {None, PartialMatchSubtype.ADJACENT_CAPABILITY_PARTIAL}
        for item in primary
    )
    partial_ownership_scope = sum(
        item.partial_match_subtype is PartialMatchSubtype.OWNERSHIP_OR_SCOPE_GAP for item in primary
    )
    diagnostics["partial_capability_present_count"] = partial_capability_present
    diagnostics["partial_adjacent_count"] = partial_adjacent
    diagnostics["partial_ownership_scope_count"] = partial_ownership_scope
    small_sample_functional_support = (
        len(primary) <= 3
        and not counts[MatchType.NO_CONFIRMED_MATCH]
        and counts[MatchType.DIRECT_MATCH]
        + counts[MatchType.TRANSFERABLE_MATCH]
        + partial_capability_present
        >= 2
    )

    if no_match_share >= 0.75 and high_count:
        result = CandidateAccessibility.POOR_FIT
    elif len(severe_dimensions) >= 2:
        result = CandidateAccessibility.ASPIRATIONAL
    elif severe_dimensions:
        result = (
            CandidateAccessibility.NEAR_TERM_TARGET
            if weighted_support >= 0.5 or small_sample_functional_support
            else CandidateAccessibility.ASPIRATIONAL
        )
    elif moderate_count:
        if weighted_support >= 0.65 and direct_share >= 0.4:
            result = CandidateAccessibility.APPLY_SELECTIVELY
        elif weighted_support >= 0.4:
            result = CandidateAccessibility.NEAR_TERM_TARGET
        else:
            result = CandidateAccessibility.ASPIRATIONAL
    elif (
        direct_share >= 0.6
        and weighted_support >= 0.75
        and not counts[MatchType.NO_CONFIRMED_MATCH]
    ):
        result = CandidateAccessibility.APPLY_NOW
    elif weighted_support >= 0.65 and direct_share >= 0.35:
        result = CandidateAccessibility.APPLY_SELECTIVELY
    elif weighted_support >= 0.4:
        result = CandidateAccessibility.NEAR_TERM_TARGET
    else:
        result = CandidateAccessibility.ASPIRATIONAL

    if result is CandidateAccessibility.APPLY_NOW and employer_specific_checks:
        result = CandidateAccessibility.APPLY_SELECTIVELY
        diagnostics["employer_specific_note"] = (
            "Some observed employers have additional requirements to check; "
            "these do not define an unmet requirement for every target opening."
        )
    if result is CandidateAccessibility.APPLY_NOW and coverage_notes:
        result = CandidateAccessibility.APPLY_SELECTIVELY
    primary_confidences = {item.confidence for item in primary}
    if role.confidence is ConfidenceLevel.LOW or ConfidenceLevel.LOW in primary_confidences:
        diagnostics["confidence_note"] = (
            "This assessment is tentative because evidence confidence is low; "
            "that uncertainty is not an additional candidate capability gap."
        )
    return result, diagnostics


def _rationale(
    accessibility: CandidateAccessibility,
    advantages: list[DemonstratedStrength],
    gaps: list[GroupedCareerGap],
    diagnostics: dict[str, object],
) -> str:
    strengths = ", ".join(item.title for item in advantages[:3])
    first = (
        f"Your strongest grounded advantages are {strengths}."
        if strengths
        else "The available evidence does not establish a strong career-level advantage."
    )
    dimensions = diagnostics["independent_severe_dimensions"]
    high_or_blocking = int(diagnostics["raw_high_gap_count"]) + int(
        diagnostics["raw_blocking_gap_count"]
    )
    mandatory = int(diagnostics["mandatory_severe_requirement_count"])
    if accessibility is CandidateAccessibility.INSUFFICIENT_CANDIDATE_EVIDENCE:
        burden = (
            "The comparison is incomplete; missing information is not a demonstrated "
            "capability deficit."
        )
    elif dimensions:
        dimension_names = ", ".join(_DIMENSION_LABELS[item] for item in dimensions)
        dimension_label = "dimension" if len(dimensions) == 1 else "dimensions"
        gap_label = "gap" if high_or_blocking == 1 else "gaps"
        requirement_label = "requirement" if mandatory == 1 else "requirements"
        verb = "contains" if len(dimensions) == 1 else "contain"
        burden = (
            f"{len(dimensions)} major remaining {dimension_label} ({dimension_names}) {verb} "
            f"{high_or_blocking} high or blocking {gap_label} across {mandatory} mandatory "
            f"{requirement_label}."
        )
    elif gaps:
        theme_label = "theme" if len(gaps) == 1 else "themes"
        verb = "requires" if len(gaps) == 1 else "require"
        burden = f"{len(gaps)} material gap {theme_label} still {verb} stronger direct evidence."
    elif diagnostics.get("coverage_note"):
        burden = "Completed comparisons support this assessment; remaining checks are unresolved."
    else:
        burden = "No material target-role gap remains in the usable comparison evidence."
    conclusions = {
        CandidateAccessibility.APPLY_NOW: (
            "Core target requirements are directly demonstrated without a material barrier, "
            "supporting Apply now."
        ),
        CandidateAccessibility.APPLY_SELECTIVELY: (
            "Substantial core evidence is present, while some employers may still require "
            "stronger direct ownership, scope, or maturity evidence; Apply selectively."
        ),
        CandidateAccessibility.NEAR_TERM_TARGET: (
            "The transition is credible, but important direct evidence still needs to be built; "
            "this is a Near-term target."
        ),
        CandidateAccessibility.ASPIRATIONAL: (
            "The remaining independent barriers or limited core support make this an "
            "Aspirational target."
        ),
        CandidateAccessibility.POOR_FIT: (
            "Hard blockers or a dominant fundamental mismatch currently make this a Poor fit."
        ),
        CandidateAccessibility.INSUFFICIENT_CANDIDATE_EVIDENCE: (
            "There is not enough approved primary-target evidence for a defensible assessment."
        ),
    }
    second = f"{burden} {conclusions[accessibility]}"
    return _bounded_text(
        f"{first} {second} {diagnostics.get('confidence_note', '')} "
        f"{diagnostics.get('employer_specific_note', '')} {diagnostics.get('coverage_note', '')}",
        900,
    )


def _assessment_summary(
    demonstrated: list[DemonstratedStrength],
    alignments: list[TargetAlignment],
    gaps: list[GroupedCareerGap],
    *,
    complete: bool = True,
) -> str:
    strength_names = ", ".join(item.title for item in demonstrated[:3])
    if strength_names:
        opening = f"You bring strong demonstrated evidence in {strength_names}."
    else:
        opening = "The available approved evidence does not yet establish a demonstrated strength."
    alignment_labels = list(
        dict.fromkeys(
            {
                TargetAlignmentType.DIRECTLY_ALIGNED: "directly",
                TargetAlignmentType.TRANSFERABLE: "transferably",
                TargetAlignmentType.PARTIALLY_ALIGNED: "partially",
            }[item.alignment_type]
            for item in alignments
        )
    )
    alignment_story = (
        "These capabilities support the target " + ", ".join(alignment_labels) + "."
        if alignment_labels
        else "Their relationship to the target could not be established reliably."
    )
    if gaps:
        missing = " and ".join(item.display_title for item in gaps[:2])
        gap_story = f"The main evidence still to build is {missing}."
    elif complete:
        gap_story = "No material target-role evidence gap remains in the usable comparison."
    else:
        gap_story = (
            "The available comparison is incomplete, so target-role gaps cannot yet be settled."
        )
    return _bounded_text(f"{opening} {alignment_story} {gap_story}", 900)


def synthesize_career_assessment(
    profile: CandidateProfile,
    role: RoleAssessment,
    analysis: MarketRequirementAnalysis,
    model_gateway: ModelGateway | None,
) -> CareerAssessmentSynthesis:
    """Group and interpret validated career findings without changing raw provenance."""

    provider = model = None
    fallback = model_gateway is None
    draft: CareerSynthesisDraft
    if model_gateway is None:
        draft = _fallback_draft(profile, role, analysis)
    else:
        try:
            response = model_gateway.generate_structured(
                role=ModelRole.REASONING,
                output_schema=CareerSynthesisDraft,
                system_prompt=SYSTEM_PROMPT,
                user_prompt=build_synthesis_prompt(_payload(profile, role, analysis)),
                temperature=0.1,
                max_tokens=3200,
                metadata={
                    "task_type": "career_assessment_synthesis",
                    "prompt_version": PROMPT_VERSION,
                    "comparison_count": len(role.requirement_comparisons),
                    "gap_count": len(material_gaps(role.gaps)),
                },
            )
            draft = CareerSynthesisDraft.model_validate(response.structured_output)
            _validate_draft(draft, role, profile, analysis)
            provider, model = response.provider, response.model
        except (ModelGatewayError, CareerSynthesisValidationError, TypeError, ValueError):
            fallback = True
            draft = _fallback_draft(profile, role, analysis)

    _validate_draft(draft, role, profile, analysis)
    gaps_by_id = {item.gap_id: item for item in material_gaps(role.gaps)}
    requirements, _ = _requirement_maps(analysis)
    comparison_by_requirement = {item.requirement_id: item for item in role.requirement_comparisons}
    grouped = []
    for item in draft.grouped_gaps:
        sources = [gaps_by_id[value] for value in item.underlying_gap_ids]
        dimensions_by_gap = [
            _gap_dimensions(gap, requirements, comparison_by_requirement) for gap in sources
        ]
        primary_dimensions = [_primary_dimension(values) for values in dimensions_by_gap]
        primary_dimension = max(
            _DIMENSION_PRIORITY,
            key=lambda value: (
                primary_dimensions.count(value),
                -_DIMENSION_PRIORITY.index(value),
            ),
        )
        affected_dimensions = [
            dimension
            for dimension in _DIMENSION_PRIORITY
            if any(dimension in values for values in dimensions_by_gap)
        ]
        affected_requirement_ids = list(
            dict.fromkeys(
                value for gap in sources for value in (gap.requirement_ids or [gap.requirement_id])
            )
        )
        grouped.append(
            GroupedCareerGap(
                **item.model_dump(),
                display_title=item.title,
                underlying_requirement_names=list(
                    dict.fromkeys(
                        name for gap in sources for name in _requirement_names(gap, requirements)
                    )
                ),
                severity=_group_severity(sources),
                requirement_frequency=max(
                    sources, key=lambda gap: _FREQUENCY_RANK[gap.requirement_frequency]
                ).requirement_frequency,
                affected_requirement_ids=affected_requirement_ids,
                underlying_gap_count=len(sources),
                high_or_blocking_gap_count=sum(
                    gap.severity in {GapSeverity.HIGH, GapSeverity.BLOCKING} for gap in sources
                ),
                mandatory_requirement_count=sum(
                    bool(requirements[requirement_id].mandatory)
                    for requirement_id in affected_requirement_ids
                    if requirement_id in requirements
                ),
                preferred_requirement_count=sum(
                    bool(requirements[requirement_id].preferred)
                    for requirement_id in affected_requirement_ids
                    if requirement_id in requirements
                ),
                primary_dimension=primary_dimension,
                affected_dimensions=affected_dimensions,
            )
        )
    advantages = [CareerAdvantage(**item.model_dump()) for item in draft.strongest_advantages]
    transfers = [TransferableStrength(**item.model_dump()) for item in draft.transferable_strengths]
    demonstrated, target_alignments = _demonstrated_story(profile, role, analysis)
    accessibility, diagnostics = _accessibility(role, analysis)
    source_comparisons = [item.comparison_id for item in role.requirement_comparisons]
    source_gaps = [item.gap_id for item in material_gaps(role.gaps)]
    source_evidence = list(
        dict.fromkeys(
            value
            for item in [*demonstrated, *target_alignments, *advantages, *transfers]
            for value in item.supporting_evidence_ids
        )
    )
    limitations = list(draft.limitations)
    coverage_notes = readiness_coverage_notes(analysis, role.requirement_comparisons)
    limitations = list(dict.fromkeys([*limitations, *coverage_notes]))
    if fallback and model_gateway is not None:
        limitations.append(
            "Semantic synthesis was unavailable; validated deterministic grouping was used."
        )
    confidence = (
        ConfidenceLevel.INSUFFICIENT
        if accessibility is CandidateAccessibility.INSUFFICIENT_CANDIDATE_EVIDENCE
        else role.confidence
    )
    if fallback and model_gateway is not None and confidence is ConfidenceLevel.HIGH:
        confidence = ConfidenceLevel.MODERATE
    if coverage_notes and confidence is ConfidenceLevel.HIGH:
        confidence = ConfidenceLevel.MODERATE
    status = (
        CareerSynthesisStatus.INSUFFICIENT
        if accessibility is CandidateAccessibility.INSUFFICIENT_CANDIDATE_EVIDENCE
        else CareerSynthesisStatus.SUCCEEDED_WITH_FALLBACK
        if fallback
        else CareerSynthesisStatus.SUCCEEDED
    )
    return CareerAssessmentSynthesis(
        target_role=role.target_role,
        accessibility=accessibility,
        confidence=confidence,
        demonstrated_strengths=demonstrated,
        target_alignments=target_alignments,
        strongest_advantages=advantages,
        transferable_strengths=transfers,
        grouped_gaps=grouped,
        assessment_summary=_assessment_summary(
            demonstrated,
            target_alignments,
            grouped,
            complete=accessibility is not CandidateAccessibility.INSUFFICIENT_CANDIDATE_EVIDENCE
            and not coverage_notes
            and bool(role.requirement_comparisons)
            and all(
                item.match_type is not None
                for item in role.requirement_comparisons
                if item.comparison_scope in _PRIMARY_SCOPES
            ),
        ),
        accessibility_rationale=_rationale(accessibility, demonstrated, grouped, diagnostics),
        source_comparison_ids=source_comparisons,
        source_gap_ids=source_gaps,
        source_evidence_ids=source_evidence,
        independent_severe_dimensions=list(diagnostics["independent_severe_dimensions"]),
        direct_match_count=diagnostics["counts"][MatchType.DIRECT_MATCH],
        transferable_match_count=diagnostics["counts"][MatchType.TRANSFERABLE_MATCH],
        partial_match_count=diagnostics["counts"][MatchType.PARTIAL_MATCH],
        partial_capability_present_count=diagnostics["partial_capability_present_count"],
        partial_adjacent_count=diagnostics["partial_adjacent_count"],
        partial_ownership_scope_count=diagnostics["partial_ownership_scope_count"],
        no_confirmed_match_count=diagnostics["counts"][MatchType.NO_CONFIRMED_MATCH],
        insufficient_comparison_count=diagnostics["insufficient_count"],
        raw_high_gap_count=diagnostics["raw_high_gap_count"],
        raw_blocking_gap_count=diagnostics["raw_blocking_gap_count"],
        limitations=limitations,
        provider=provider,
        model=model,
        prompt_version=PROMPT_VERSION,
        status=status,
    )
