"""Evidence-grounded candidate-to-market requirement comparison."""

import logging
import re
from collections import Counter
from time import perf_counter
from uuid import UUID, uuid4

from ai_career_navigator.domain import (
    CandidateProfile,
    ComparisonScope,
    ConfidenceLevel,
    EvidenceItem,
    EvidenceMaturity,
    FunctionalOverlap,
    MatchType,
    MaturityAlignment,
    OwnershipAlignment,
    PartialMatchSubtype,
    ProductionContextDifference,
    RequirementCategory,
    RequirementComparison,
    RoleRequirement,
    ScopeAlignment,
)
from ai_career_navigator.market import MarketRequirementAnalysis, PostingTitleMatch
from ai_career_navigator.models import ModelGateway, ModelGatewayError, ModelRole

from .comparison_prompts import PROMPT_VERSION, SYSTEM_PROMPT, build_transferability_prompt
from .comparison_schemas import (
    CandidateComparisonResult,
    CandidateComparisonStatus,
    TransferabilityAssessment,
)
from .errors import TransferabilityAssessmentError

logger = logging.getLogger(__name__)
_MATURITY = {value: index for index, value in enumerate(EvidenceMaturity)}
_HARD_CATEGORIES = {
    RequirementCategory.CREDENTIAL,
    RequirementCategory.WORK_AUTHORIZATION,
    RequirementCategory.LANGUAGE,
}
_GENERIC_ROLE_TOKENS = {
    "analyst",
    "architect",
    "consultant",
    "developer",
    "engineer",
    "lead",
    "manager",
    "senior",
    "specialist",
}
_GENERIC_LOCATION_TOKENS = {
    "location",
    "canada",
    "canadian",
    "ca",
    "on",
    "ontario",
    "bc",
    "alberta",
    "quebec",
    "onsite",
    "hybrid",
    "remote",
}
_WORK_ARRANGEMENT_TOKENS = {"onsite", "hybrid", "remote"}


def normalize_capability(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9+#.]+", value.casefold()))


def eligible_candidate_evidence(profile: CandidateProfile) -> list[EvidenceItem]:
    return list(profile.approved_evidence_items)


def _location_context_comparison(
    profile: CandidateProfile,
    requirement: RoleRequirement,
    scope: ComparisonScope,
) -> RequirementComparison | None:
    """Use confirmed profile location without pretending it proves work-mode willingness."""

    if requirement.category is not RequirementCategory.LOCATION or not profile.current_location:
        return None
    target = set(
        normalize_capability(
            requirement.normalized_capability or requirement.requirement_text
        ).split()
    )
    candidate = set(normalize_capability(profile.current_location).split())
    target_specific = target - _GENERIC_LOCATION_TOKENS
    candidate_specific = candidate - _GENERIC_LOCATION_TOKENS
    geography_aligned = bool(
        (target_specific and target_specific & candidate_specific)
        or (not target_specific and target & candidate)
    )
    if not geography_aligned:
        return None
    arrangement = target & _WORK_ARRANGEMENT_TOKENS
    partial = bool(arrangement)
    return RequirementComparison(
        requirement_id=requirement.requirement_id,
        posting_id=requirement.posting_id,
        comparison_scope=scope,
        functional_overlap=FunctionalOverlap.HIGH,
        ownership_alignment=OwnershipAlignment.NOT_APPLICABLE,
        scope_alignment=ScopeAlignment.PARTIAL if partial else ScopeAlignment.ALIGNED,
        maturity_alignment=MaturityAlignment.UNKNOWN,
        production_context_difference=ProductionContextDifference.UNKNOWN,
        partial_match_subtype=(
            PartialMatchSubtype.ADJACENT_CAPABILITY_PARTIAL if partial else None
        ),
        match_type=MatchType.PARTIAL_MATCH if partial else MatchType.DIRECT_MATCH,
        remaining_difference=(
            "Current location aligns, but the required work arrangement is not confirmed."
            if partial
            else "No material location difference identified."
        ),
        explanation="Compared against the user-confirmed current profile location.",
        confidence=ConfidenceLevel.MODERATE if partial else ConfidenceLevel.HIGH,
    )


def _scope_by_posting(analysis: MarketRequirementAnalysis) -> dict[UUID, ComparisonScope]:
    return {
        item.candidate.posting_id: {
            PostingTitleMatch.EXACT_TARGET: ComparisonScope.EXACT_TARGET,
            PostingTitleMatch.TARGET_VARIANT: ComparisonScope.TARGET_VARIANT,
            PostingTitleMatch.RELATED_TITLE: ComparisonScope.RELATED_TITLE,
        }[item.title_match]
        for item in analysis.assessments
        if item.title_match is not PostingTitleMatch.IRRELEVANT
    }


def _explicit_years(item: EvidenceItem) -> float | None:
    text = " ".join(filter(None, [item.description, item.context, item.outcome]))
    values = re.findall(r"\b(\d+(?:\.\d+)?)\s*\+?\s*years?\b", text, re.IGNORECASE)
    return max((float(value) for value in values), default=None)


def _deterministic(
    requirement: RoleRequirement,
    evidence: list[EvidenceItem],
    scope: ComparisonScope,
) -> RequirementComparison | None:
    target = normalize_capability(requirement.normalized_capability or requirement.requirement_text)
    exact = [item for item in evidence if normalize_capability(item.capability) == target]
    if exact:
        best = max(exact, key=lambda item: _MATURITY[item.maturity_level])
        maturity_short = bool(
            requirement.maturity_expected
            and _MATURITY[best.maturity_level] < _MATURITY[requirement.maturity_expected]
        )
        years = max(
            (value for item in exact if (value := _explicit_years(item)) is not None),
            default=None,
        )
        years_short = bool(
            requirement.years_required and years is not None and years < requirement.years_required
        )
        years_unknown = bool(requirement.years_required and years is None)
        partial = maturity_short or years_short or years_unknown
        if maturity_short:
            difference = (
                f"Confirmed {best.maturity_level.value.lower()} evidence is below the "
                f"required {requirement.maturity_expected.value.lower()} maturity."
            )
        elif years_short:
            difference = (
                f"Confirmed relevant experience ({years:g} years) is below the posting's "
                f"{requirement.years_required:g}-year requirement."
            )
        elif years_unknown:
            difference = "Relevant evidence exists, but explicit years are not confirmed."
        else:
            difference = "No material difference identified."
        return RequirementComparison(
            requirement_id=requirement.requirement_id,
            posting_id=requirement.posting_id,
            comparison_scope=scope,
            evidence_ids=[item.evidence_id for item in exact],
            candidate_maturity=best.maturity_level,
            target_maturity=requirement.maturity_expected,
            functional_overlap=FunctionalOverlap.HIGH,
            ownership_alignment=OwnershipAlignment.ALIGNED,
            scope_alignment=ScopeAlignment.ALIGNED,
            maturity_alignment=(
                MaturityAlignment.BELOW_TARGET
                if maturity_short
                else MaturityAlignment.UNKNOWN
                if requirement.maturity_expected is None
                else MaturityAlignment.ALIGNED
            ),
            production_context_difference=(
                ProductionContextDifference.PROJECT_TO_PRODUCTION
                if maturity_short
                and best.evidence_type.casefold() == "project"
                and requirement.maturity_expected
                in {
                    EvidenceMaturity.APPLIED,
                    EvidenceMaturity.PRODUCTION,
                    EvidenceMaturity.LEADERSHIP,
                }
                else ProductionContextDifference.LIMITED_PRODUCTION_DEPTH
                if maturity_short
                else ProductionContextDifference.NONE
            ),
            partial_match_subtype=(
                PartialMatchSubtype.CAPABILITY_PRESENT_MATURITY_GAP if partial else None
            ),
            match_type=MatchType.PARTIAL_MATCH if partial else MatchType.DIRECT_MATCH,
            remaining_difference=difference,
            explanation="Compared using exact normalized capability and confirmed evidence.",
            confidence=ConfidenceLevel.MODERATE if years_unknown else ConfidenceLevel.HIGH,
        )
    if requirement.category in _HARD_CATEGORIES:
        return RequirementComparison(
            requirement_id=requirement.requirement_id,
            posting_id=requirement.posting_id,
            comparison_scope=scope,
            match_type=MatchType.NO_CONFIRMED_MATCH,
            functional_overlap=FunctionalOverlap.NONE,
            ownership_alignment=OwnershipAlignment.MISSING,
            scope_alignment=ScopeAlignment.UNKNOWN,
            maturity_alignment=MaturityAlignment.UNKNOWN,
            production_context_difference=ProductionContextDifference.UNKNOWN,
            remaining_difference="No confirmed evidence was found for "
            f"{requirement.normalized_capability or requirement.requirement_text}.",
            explanation="Hard prerequisites require directly confirmed evidence.",
            confidence=ConfidenceLevel.HIGH,
        )
    return None


def _candidate_set(
    requirement: RoleRequirement, evidence: list[EvidenceItem]
) -> list[EvidenceItem]:
    def terms(value: str) -> set[str]:
        def stem(token: str) -> str:
            for suffix in ("ments", "ment", "ing", "ers", "er", "ed", "s"):
                if token.endswith(suffix) and len(token) - len(suffix) >= 4:
                    return token[: -len(suffix)]
            return token

        return {stem(token) for token in normalize_capability(value).split()}

    target_tokens = terms(requirement.normalized_capability or requirement.requirement_text)
    scored: list[tuple[tuple[int, int, int, int, int], EvidenceItem]] = []
    for item in evidence:
        capability_tokens = terms(item.capability)
        detail_tokens = terms(
            " ".join(filter(None, [item.description, item.context, item.outcome, item.metric]))
        )
        capability_overlap = len(target_tokens & capability_tokens)
        detail_overlap = len(target_tokens & detail_tokens)
        generic_title = bool(
            item.evidence_type.casefold() == "employment"
            and normalize_capability(item.capability) in normalize_capability(item.source_reference)
        )
        specific_tokens = capability_tokens - _GENERIC_ROLE_TOKENS
        source_quality = {
            "skill": 4,
            "project": 4,
            "employment": 2,
            "certification": 2,
            "education": 1,
        }.get(item.evidence_type.casefold(), 1)
        semantic_relevance = capability_overlap * 5 + detail_overlap * 2
        if specific_tokens and capability_overlap:
            semantic_relevance += 3
        if generic_title:
            semantic_relevance -= 4
        scored.append(
            (
                (
                    semantic_relevance,
                    int(bool(specific_tokens)),
                    min(len(specific_tokens), 6),
                    source_quality,
                    _MATURITY[item.maturity_level],
                ),
                item,
            )
        )
    positive = [
        item
        for score, item in sorted(scored, key=lambda pair: pair[0], reverse=True)
        if score[0] > 0
    ]
    if positive:
        return positive[:8]
    return [item for _, item in sorted(scored, key=lambda pair: pair[0], reverse=True)[:5]]


def _maturity_alignment(
    candidate: EvidenceMaturity | None, target: EvidenceMaturity | None
) -> MaturityAlignment:
    if candidate is None or target is None:
        return MaturityAlignment.UNKNOWN
    return (
        MaturityAlignment.BELOW_TARGET
        if _MATURITY[candidate] < _MATURITY[target]
        else MaturityAlignment.ALIGNED
    )


def _production_difference(
    proposed: ProductionContextDifference,
    supporting: list[EvidenceItem],
    candidate: EvidenceMaturity | None,
    target: EvidenceMaturity | None,
) -> ProductionContextDifference:
    alignment = _maturity_alignment(candidate, target)
    if alignment is not MaturityAlignment.BELOW_TARGET:
        return ProductionContextDifference.NONE if target is not None else proposed
    if any(item.evidence_type.casefold() == "project" for item in supporting) and candidate in {
        EvidenceMaturity.EXPOSURE,
        EvidenceMaturity.DEMONSTRATED,
    }:
        return ProductionContextDifference.PROJECT_TO_PRODUCTION
    if candidate in {EvidenceMaturity.APPLIED, EvidenceMaturity.PRODUCTION}:
        return ProductionContextDifference.LIMITED_PRODUCTION_DEPTH
    return proposed


def _partial_subtype(
    assessment: TransferabilityAssessment,
    maturity_alignment: MaturityAlignment,
    production_difference: ProductionContextDifference,
) -> PartialMatchSubtype:
    if assessment.functional_overlap is FunctionalOverlap.HIGH and (
        maturity_alignment is MaturityAlignment.BELOW_TARGET
        or production_difference
        in {
            ProductionContextDifference.PROJECT_TO_PRODUCTION,
            ProductionContextDifference.LIMITED_PRODUCTION_DEPTH,
        }
    ):
        return PartialMatchSubtype.CAPABILITY_PRESENT_MATURITY_GAP
    if assessment.functional_overlap in {FunctionalOverlap.HIGH, FunctionalOverlap.MODERATE} and (
        assessment.ownership_alignment in {OwnershipAlignment.PARTIAL, OwnershipAlignment.MISSING}
        or assessment.scope_alignment in {ScopeAlignment.PARTIAL, ScopeAlignment.MISSING}
    ):
        return PartialMatchSubtype.OWNERSHIP_OR_SCOPE_GAP
    return PartialMatchSubtype.ADJACENT_CAPABILITY_PARTIAL


def _semantic(
    requirement: RoleRequirement,
    candidates: list[EvidenceItem],
    scope: ComparisonScope,
    gateway: ModelGateway,
) -> RequirementComparison:
    response = gateway.generate_structured(
        role=ModelRole.REASONING,
        output_schema=TransferabilityAssessment,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=build_transferability_prompt(requirement, candidates),
        temperature=0,
        max_tokens=1200,
        metadata={
            "task_type": "candidate_requirement_comparison",
            "prompt_version": PROMPT_VERSION,
        },
    )
    assessment = TransferabilityAssessment.model_validate(response.structured_output)
    if assessment.requirement_id != requirement.requirement_id:
        raise TransferabilityAssessmentError("model returned a different requirement reference")
    allowed = {item.evidence_id for item in candidates}
    if not set(assessment.supporting_evidence_ids).issubset(allowed):
        raise TransferabilityAssessmentError("model returned an unsupported evidence reference")
    supporting = [
        item for item in candidates if item.evidence_id in assessment.supporting_evidence_ids
    ]
    candidate_maturity = (
        max((item.maturity_level for item in supporting), key=_MATURITY.get) if supporting else None
    )
    target_maturity = requirement.maturity_expected
    maturity_alignment = _maturity_alignment(candidate_maturity, target_maturity)
    production_difference = _production_difference(
        assessment.production_context_difference,
        supporting,
        candidate_maturity,
        target_maturity,
    )
    partial_subtype = (
        _partial_subtype(assessment, maturity_alignment, production_difference)
        if assessment.match_type is MatchType.PARTIAL_MATCH
        else None
    )
    return RequirementComparison(
        requirement_id=requirement.requirement_id,
        posting_id=requirement.posting_id,
        comparison_scope=scope,
        evidence_ids=assessment.supporting_evidence_ids,
        candidate_maturity=candidate_maturity,
        target_maturity=target_maturity,
        functional_overlap=assessment.functional_overlap,
        ownership_alignment=assessment.ownership_alignment,
        scope_alignment=assessment.scope_alignment,
        maturity_alignment=maturity_alignment,
        production_context_difference=production_difference,
        partial_match_subtype=partial_subtype,
        match_type=assessment.match_type,
        transferable_capability=assessment.transferable_capability,
        remaining_difference=assessment.remaining_difference,
        explanation=assessment.explanation,
        confidence=assessment.confidence,
    )


_PRODUCT_OWNERSHIP_REQUIREMENTS = (
    "product vision",
    "product strategy",
    "product ownership",
    "roadmap ownership",
    "lifecycle ownership",
)
_PRODUCT_OWNERSHIP_EVIDENCE = (
    "product vision",
    "product strategy",
    "product owner",
    "product ownership",
    "roadmap ownership",
    "owned the roadmap",
    "accountable for the roadmap",
    "lifecycle ownership",
)


def _enforce_transferability_quality(
    requirement: RoleRequirement,
    candidates: list[EvidenceItem],
    comparison: RequirementComparison,
) -> RequirementComparison:
    """Prevent adjacent discovery evidence from becoming unsupported product ownership."""

    if comparison.match_type is not MatchType.TRANSFERABLE_MATCH:
        return comparison
    if (
        comparison.ownership_alignment in {OwnershipAlignment.MISSING, OwnershipAlignment.PARTIAL}
        or comparison.scope_alignment in {ScopeAlignment.MISSING, ScopeAlignment.PARTIAL}
        or comparison.maturity_alignment is MaturityAlignment.BELOW_TARGET
        or comparison.production_context_difference
        in {
            ProductionContextDifference.PROJECT_TO_PRODUCTION,
            ProductionContextDifference.LIMITED_PRODUCTION_DEPTH,
        }
    ):
        subtype = (
            PartialMatchSubtype.CAPABILITY_PRESENT_MATURITY_GAP
            if comparison.maturity_alignment is MaturityAlignment.BELOW_TARGET
            or comparison.production_context_difference
            in {
                ProductionContextDifference.PROJECT_TO_PRODUCTION,
                ProductionContextDifference.LIMITED_PRODUCTION_DEPTH,
            }
            else PartialMatchSubtype.OWNERSHIP_OR_SCOPE_GAP
        )
        return comparison.model_copy(
            update={"match_type": MatchType.PARTIAL_MATCH, "partial_match_subtype": subtype}
        )
    target = normalize_capability(requirement.normalized_capability or requirement.requirement_text)
    if not any(term in target for term in _PRODUCT_OWNERSHIP_REQUIREMENTS):
        return comparison
    supporting_ids = set(comparison.evidence_ids)
    supporting_text = " ".join(
        normalize_capability(
            " ".join(filter(None, [item.capability, item.description, item.context, item.outcome]))
        )
        for item in candidates
        if item.evidence_id in supporting_ids
    )
    if any(term in supporting_text for term in _PRODUCT_OWNERSHIP_EVIDENCE):
        return comparison
    return comparison.model_copy(
        update={
            "match_type": MatchType.PARTIAL_MATCH,
            "partial_match_subtype": PartialMatchSubtype.OWNERSHIP_OR_SCOPE_GAP,
            "ownership_alignment": OwnershipAlignment.MISSING,
            "remaining_difference": (
                comparison.remaining_difference
                or "Adjacent evidence is present, but direct product ownership is not confirmed."
            ),
            "explanation": (
                "Adjacent evidence supports part of this requirement, but direct product "
                "vision, strategy, or roadmap ownership is not confirmed."
            ),
        }
    )


def compare_candidate_to_requirements(
    profile: CandidateProfile,
    analysis: MarketRequirementAnalysis,
    model_gateway: ModelGateway,
) -> CandidateComparisonResult:
    """Prefer deterministic comparison, using reasoning only for semantic transfer."""

    started = perf_counter()
    evidence = eligible_candidate_evidence(profile)
    scopes = _scope_by_posting(analysis)
    canonical_by_id = {
        item.canonical_requirement_id: item
        for item in (
            analysis.canonical_profile.comparison_requirements if analysis.canonical_profile else ()
        )
    }
    if canonical_by_id:
        requirements = [
            item.as_role_requirement()
            for item in analysis.canonical_profile.comparison_requirements
        ]
        canonical_scopes = {
            item.canonical_requirement_id: (
                ComparisonScope.EXACT_TARGET
                if item.exact_support_count
                else ComparisonScope.TARGET_VARIANT
            )
            for item in analysis.canonical_profile.comparison_requirements
        }
    else:
        requirements = sorted(
            (item for item in analysis.requirements if item.posting_id in scopes),
            key=lambda item: {
                ComparisonScope.EXACT_TARGET: 0,
                ComparisonScope.TARGET_VARIANT: 1,
                ComparisonScope.RELATED_TITLE: 2,
                ComparisonScope.COMBINED_RELATED: 2,
            }[scopes[item.posting_id]],
        )
        canonical_scopes = {}
    if not requirements:
        return CandidateComparisonResult(
            status=CandidateComparisonStatus.INSUFFICIENT_MARKET_REQUIREMENTS,
            limitations=["No usable posting-level market requirements were available."],
        )
    if not evidence:
        return CandidateComparisonResult(
            status=CandidateComparisonStatus.INSUFFICIENT_CANDIDATE_EVIDENCE,
            limitations=["No approved candidate evidence was available for comparison."],
        )

    comparisons: list[RequirementComparison] = []
    limitations: list[str] = []
    deterministic_count = semantic_count = failed_count = 0
    semantic_cache: dict[tuple[object, ...], RequirementComparison] = {}
    for requirement in requirements:
        scope = canonical_scopes.get(requirement.requirement_id, scopes.get(requirement.posting_id))
        if scope is None:
            continue
        source_requirement_ids = (
            canonical_by_id[requirement.requirement_id].comparison_requirement_ids
            if requirement.requirement_id in canonical_by_id
            else [requirement.requirement_id]
        )
        comparison = _location_context_comparison(profile, requirement, scope) or _deterministic(
            requirement, evidence, scope
        )
        if comparison:
            deterministic_count += 1
            comparisons.append(
                comparison.model_copy(update={"source_requirement_ids": source_requirement_ids})
            )
            continue
        candidates = _candidate_set(requirement, evidence)
        cache_key = (
            scope,
            requirement.category,
            normalize_capability(requirement.normalized_capability or requirement.requirement_text),
            requirement.years_required,
            requirement.maturity_expected,
            requirement.mandatory,
            requirement.preferred,
        )
        if cache_key in semantic_cache:
            cached = semantic_cache[cache_key]
            comparisons.append(
                cached.model_copy(
                    update={
                        "comparison_id": uuid4(),
                        "requirement_id": requirement.requirement_id,
                        "posting_id": requirement.posting_id,
                        "source_requirement_ids": source_requirement_ids,
                    }
                )
            )
            continue
        try:
            semantic_result = _enforce_transferability_quality(
                requirement,
                candidates,
                _semantic(requirement, candidates, scope, model_gateway),
            )
            semantic_result = semantic_result.model_copy(
                update={"source_requirement_ids": source_requirement_ids}
            )
            comparisons.append(semantic_result)
            semantic_cache[cache_key] = semantic_result
            semantic_count += 1
        except (ModelGatewayError, TransferabilityAssessmentError, TypeError, ValueError):
            failed_count += 1
            limitations.append(
                f"Semantic comparison was unavailable for requirement {requirement.requirement_id}."
            )
            insufficient = RequirementComparison(
                requirement_id=requirement.requirement_id,
                posting_id=requirement.posting_id,
                comparison_scope=scope,
                match_type=None,
                remaining_difference="Available evidence could not be compared responsibly.",
                confidence=ConfidenceLevel.INSUFFICIENT,
                source_requirement_ids=source_requirement_ids,
            )
            comparisons.append(insufficient)
            semantic_cache[cache_key] = insufficient

    if failed_count == len(comparisons):
        status = CandidateComparisonStatus.INSUFFICIENT_ANALYSIS
    elif failed_count:
        status = CandidateComparisonStatus.PARTIAL
    else:
        status = CandidateComparisonStatus.SUCCEEDED
    counts = Counter(
        item.match_type.value if item.match_type else "INSUFFICIENT" for item in comparisons
    )
    logger.info(
        "candidate_comparison_completed requirement_count=%d deterministic_count=%d "
        "semantic_count=%d "
        "failed_count=%d direct_count=%d transferable_count=%d partial_count=%d no_match_count=%d "
        "model_role=%s elapsed_ms=%d",
        len(requirements),
        deterministic_count,
        semantic_count,
        failed_count,
        counts[MatchType.DIRECT_MATCH.value],
        counts[MatchType.TRANSFERABLE_MATCH.value],
        counts[MatchType.PARTIAL_MATCH.value],
        counts[MatchType.NO_CONFIRMED_MATCH.value],
        ModelRole.REASONING.value,
        (perf_counter() - started) * 1000,
    )
    return CandidateComparisonResult(
        status=status,
        comparisons=comparisons,
        limitations=limitations,
        deterministic_count=deterministic_count,
        semantic_count=semantic_count,
        failed_count=failed_count,
    )
