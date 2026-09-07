"""Evidence-grounded candidate-to-market requirement comparison."""

import json
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
    distinct = {float(value) for value in values}
    return next(iter(distinct)) if len(distinct) == 1 else None


def _deterministic(
    requirement: RoleRequirement,
    evidence: list[EvidenceItem],
    scope: ComparisonScope,
) -> RequirementComparison | None:
    target = normalize_capability(requirement.normalized_capability or requirement.requirement_text)
    exact = [item for item in evidence if normalize_capability(item.capability) == target]
    # Only a simple, explicitly exercised atomic skill can use the factual shortcut.
    # Compound capabilities and qualified expectations need a semantic assessment.
    simple_skill = (
        requirement.category is RequirementCategory.TECHNICAL
        and len(target.split()) == 1
        and normalize_capability(requirement.requirement_text) in {target, f"{target} required"}
    )
    exercised = [
        item
        for item in exact
        if item.evidence_type.casefold() == "skill"
        and re.search(
            r"\b(?:used|usage|built|developed|implemented|deployed|delivered|programmed)\b",
            item.description,
            re.I,
        )
        and not re.search(
            r"\b(?:not|never|without|only|lack\w*|no)\b",
            " ".join(filter(None, [item.description, item.context, item.outcome])),
            re.I,
        )
    ]
    if simple_skill and exercised:
        exact = exercised
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
            ownership_alignment=OwnershipAlignment.NOT_APPLICABLE,
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
                PartialMatchSubtype.CAPABILITY_PRESENT_MATURITY_GAP
                if partial and not years_unknown
                else None
            ),
            match_type=(
                None
                if years_unknown
                else MatchType.PARTIAL_MATCH
                if partial
                else MatchType.DIRECT_MATCH
            ),
            remaining_difference=difference,
            explanation="Compared using exact normalized capability and confirmed evidence.",
            confidence=ConfidenceLevel.INSUFFICIENT if years_unknown else best.confidence,
            evidence_status="UNKNOWN" if years_unknown else "SUPPORTED",
            clarification_needed=(
                "How many years have you used this capability?" if years_unknown else None
            ),
            validation_notes=[
                "Simple atomic skill checked against an explicit usage statement; "
                "no ownership or scale claim inferred."
            ],
        )
    prerequisite_evidence = [
        item
        for item in evidence
        if item.evidence_type.casefold()
        in {"credential", "certification", "education", "language", "work_authorization"}
        or re.search(
            r"\b(?:licen[sc]\w*|certif\w*|authori[sz]\w*|permit|citizen\w*|fluent|bilingual)\b",
            " ".join([item.capability, item.description]),
            re.I,
        )
    ]
    if requirement.category in _HARD_CATEGORIES and not exact and not prerequisite_evidence:
        return RequirementComparison(
            requirement_id=requirement.requirement_id,
            posting_id=requirement.posting_id,
            comparison_scope=scope,
            match_type=None,
            functional_overlap=FunctionalOverlap.NONE,
            ownership_alignment=OwnershipAlignment.NOT_APPLICABLE,
            scope_alignment=ScopeAlignment.UNKNOWN,
            maturity_alignment=MaturityAlignment.UNKNOWN,
            production_context_difference=ProductionContextDifference.UNKNOWN,
            remaining_difference="No confirmed evidence was found for "
            f"{requirement.normalized_capability or requirement.requirement_text}.",
            explanation=(
                "This prerequisite has not been addressed in the confirmed profile; "
                "absence is not proof of ineligibility."
            ),
            confidence=ConfidenceLevel.INSUFFICIENT,
            evidence_status="UNKNOWN",
            clarification_needed=(
                f"Can you confirm whether you meet: {requirement.requirement_text}?"
            ),
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

    target_tokens = terms(
        f"{requirement.normalized_capability or ''} {requirement.requirement_text}"
    ) - {"required", "require", "experience", "candidate", "must", "with", "have", "and", "the"}
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
    ranked = [item for _, item in sorted(scored, key=lambda pair: pair[0], reverse=True)]
    if len(ranked) <= 12:
        return ranked
    # Reserve context for concrete professional/project examples even when they
    # use different vocabulary. Repeated skill labels cannot consume every slot.
    selected = ranked[:8]
    source_keys = {(item.evidence_type, item.source_reference) for item in selected}
    for item in ranked[8:]:
        source_key = (item.evidence_type, item.source_reference)
        if source_key in source_keys or item.evidence_type.casefold() == "skill":
            continue
        selected.append(item)
        source_keys.add(source_key)
        if len(selected) == 12:
            break
    selected_ids = {item.evidence_id for item in selected}
    selected.extend(item for item in ranked if item.evidence_id not in selected_ids)
    return selected[:12]


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
        return proposed
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
        max_tokens=2400,
        metadata={
            "task_type": "candidate_requirement_comparison",
            "prompt_version": PROMPT_VERSION,
            "requirement_id": str(requirement.requirement_id),
        },
    )
    assessment = TransferabilityAssessment.model_validate(response.structured_output)
    if assessment.requirement_id != requirement.requirement_id:
        raise TransferabilityAssessmentError("model returned a different requirement reference")
    if assessment.matched_alternative is not None and (
        requirement.relationship != "ANY_OF"
        or assessment.matched_alternative not in requirement.capability_options
    ):
        raise TransferabilityAssessmentError("model returned an unsupported alternative")
    if (
        requirement.relationship == "ANY_OF"
        and assessment.match_type in {MatchType.DIRECT_MATCH, MatchType.TRANSFERABLE_MATCH}
        and not assessment.matched_alternative
    ):
        raise TransferabilityAssessmentError(
            "positive alternative match must identify its supported option"
        )
    allowed = {item.evidence_id for item in candidates}
    if not set(assessment.supporting_evidence_ids).issubset(allowed):
        raise TransferabilityAssessmentError("model returned an unsupported evidence reference")
    by_id = {item.evidence_id: item for item in candidates}
    for excerpt in assessment.evidence_quotes:
        source = by_id.get(excerpt.evidence_id)
        if source is None or not any(
            excerpt.quote in value
            for value in (source.description, source.context, source.outcome, source.metric)
            if value
        ):
            raise TransferabilityAssessmentError(
                "model quote is not an exact candidate evidence excerpt"
            )
        if (
            assessment.match_type
            in {MatchType.DIRECT_MATCH, MatchType.TRANSFERABLE_MATCH, MatchType.PARTIAL_MATCH}
            and excerpt.evidence_id not in assessment.supporting_evidence_ids
        ):
            raise TransferabilityAssessmentError(
                "support excerpt is not linked to supporting evidence"
            )
    if assessment.match_type is MatchType.DIRECT_MATCH:
        quoted_dimensions = {
            dimension for item in assessment.evidence_quotes for dimension in item.dimensions
        }
        required_dimensions = _required_dimensions(requirement)
        if not required_dimensions.issubset(quoted_dimensions):
            raise TransferabilityAssessmentError(
                "direct match does not ground the material expectation"
            )
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
        outcome_alignment=assessment.outcome_alignment,
        matched_alternative=assessment.matched_alternative,
        evidence_status=(
            "SUPPORTED"
            if assessment.evidence_status == "UNKNOWN"
            and assessment.match_type
            in {MatchType.DIRECT_MATCH, MatchType.TRANSFERABLE_MATCH, MatchType.PARTIAL_MATCH}
            else assessment.evidence_status
        ),
        clarification_needed=assessment.clarification_needed,
        grounded_evidence_quotes=[
            {
                "evidence_id": str(item.evidence_id),
                "quote": item.quote,
                "dimensions": ",".join(item.dimensions),
            }
            for item in assessment.evidence_quotes
        ],
        validation_notes=(
            [
                "Production context corrected from "
                f"{assessment.production_context_difference.value} "
                f"to {production_difference.value} using the confirmed maturity difference."
            ]
            if production_difference is not assessment.production_context_difference
            else []
        ),
        partial_match_subtype=partial_subtype,
        match_type=assessment.match_type,
        transferable_capability=assessment.transferable_capability,
        remaining_difference=assessment.remaining_difference,
        explanation=assessment.explanation,
        confidence=(
            ConfidenceLevel.INSUFFICIENT if assessment.match_type is None else assessment.confidence
        ),
    )


def _requires_ownership(requirement: RoleRequirement) -> bool:
    return bool(
        re.search(
            r"\b(?:own|owns|ownership|accountable|accountability|decision authority)\b",
            f"{requirement.normalized_capability or ''} {requirement.requirement_text}",
            re.I,
        )
    )


def _required_dimensions(requirement: RoleRequirement) -> set[str]:
    text = f"{requirement.normalized_capability or ''} {requirement.requirement_text}"
    dimensions = {"function"}
    if _requires_ownership(requirement):
        dimensions.add("ownership")
    if re.search(r"\bproduction\b", text, re.I):
        dimensions.add("production")
    if re.search(
        r"\b(?:enterprise.scale|large.scale|high.volume|global scale|million\w*)\b", text, re.I
    ):
        dimensions.add("scope")
    if re.search(
        r"\b(?:measurable outcomes?|revenue|cost reduction|business results|KPIs?)\b", text, re.I
    ):
        dimensions.add("outcome")
    return dimensions


def _ownership_claim_supported(text: str) -> bool:
    """Require an affirmative candidate action, not a model-assigned quote tag.

    This intentionally recognizes several forms of decision accountability without
    claiming that a literal occurrence of "owned" proves ownership of the target.
    Attribution to a supported manager or a hypothetical future action is not proof.
    """

    subject = r"(?:(?:i|we|the candidate)\s+)?(?:personally\s+)?"
    action = (
        r"(?:owned|owns)\b|"
        r"(?:(?:was|am|were|is)\s+)?(?:personally\s+)?accountable\s+for\b|"
        r"(?:held|hold|had|exercised)\s+(?:final\s+)?decision\s+(?:rights|authority)\b|"
        r"(?:signed|sign)\s+off\b|"
        r"(?:held|had|gave|provided)\s+final\s+(?:approval|sign[ -]off)\b|"
        r"(?:acted|served)\s+as\s+(?:the\s+)?final\s+approver\b|"
        r"(?:set|defined|established)\s+(?:the\s+)?(?:strategic\s+)?"
        r"(?:direction|priorities|strategy)\b|"
        r"(?:made|took)\s+(?:the\s+)?(?:final|strategic)\s+decisions\b|"
        r"(?:took|held|had)\s+(?:personal\s+)?accountability\s+for\b|"
        r"(?:(?:was|am|were|is)\s+)?responsible\s+for\s+(?:the\s+)?"
        r"(?:outcomes?|decisions?|results|delivery outcomes?|performance|budget)\b"
    )
    for clause in re.split(r"[.;,\n]+|\band\s+(?=(?:i\s+)?(?:owned|held|signed|set)\b)", text):
        if re.match(rf"^\s*{subject}(?:{action})", clause, re.I):
            return True
    return False


def _explicit_negative_requirement_claim(
    requirement: RoleRequirement, comparison: RequirementComparison
) -> bool:
    """Require both the named expectation and an explicit negative source premise."""

    aliases = {
        "registered": "registration",
        "licence": "license",
        "licensed": "license",
        "licensure": "license",
        "authorized": "authorization",
        "authorised": "authorization",
        "authorisation": "authorization",
        "canadian": "canada",
    }
    ignored = {
        "a",
        "an",
        "the",
        "and",
        "or",
        "must",
        "required",
        "requirement",
        "requires",
        "require",
        "hold",
        "have",
        "has",
        "be",
        "in",
        "of",
        "to",
        "for",
        "with",
        "professional",
        "current",
        "valid",
    }

    def tokens(text: str) -> set[str]:
        return {aliases.get(value, value) for value in normalize_capability(text).split()} - ignored

    required = tokens(requirement.normalized_capability or requirement.requirement_text)
    if not required:
        return False
    for excerpt in comparison.grounded_evidence_quotes:
        for clause in re.split(r"[.;,\n]+", excerpt.get("quote", "")):
            if "?" in clause or not required.issubset(tokens(clause)):
                continue
            if re.search(
                r"\b(?:not|cannot|can't|don't|doesn't|didn't)\s+(?:currently\s+)?"
                r"(?:hold|have|possess|meet|satisfy|eligible|authori[sz]ed|registered|"
                r"licensed|fluent|obtained|completed)\b",
                clause,
                re.I,
            ):
                return True
            if re.match(
                r"\s*(?:(?:i|we)\s+)?(?:have\s+)?(?:no|lack|lack[s]?|lacking)\b", clause, re.I
            ):
                return True
            if re.search(
                r"\b(?:expired|revoked|suspended|absent|missing)\b", clause, re.I
            ) and not re.search(r"\b(?:not|never|no)\b", clause, re.I):
                return True
    return False


def _enforce_transferability_quality(
    requirement: RoleRequirement,
    candidates: list[EvidenceItem],
    comparison: RequirementComparison,
) -> RequirementComparison:
    """Enforce generic dimensional consistency without profession-specific overrides."""

    if comparison.evidence_status in {"CONFIRMED_UNMET", "CONTRADICTED"} and (
        comparison.match_type is not MatchType.NO_CONFIRMED_MATCH
        or not _explicit_negative_requirement_claim(requirement, comparison)
    ):
        return comparison.model_copy(
            update={
                "match_type": None,
                "evidence_status": "UNKNOWN",
                "partial_match_subtype": None,
                "confidence": ConfidenceLevel.INSUFFICIENT,
                "remaining_difference": (
                    "The source does not explicitly establish that this requirement is unmet."
                ),
                "clarification_needed": (
                    f"Can you confirm whether you meet: {requirement.requirement_text}?"
                ),
                "validation_notes": [
                    *comparison.validation_notes,
                    "Unmet classification withheld: an exact quote alone does not prove "
                    "a relevant negative claim.",
                ],
            }
        )
    if comparison.match_type not in {MatchType.DIRECT_MATCH, MatchType.TRANSFERABLE_MATCH}:
        return comparison
    required_dimensions = _required_dimensions(requirement)
    unresolved = []
    if (
        "production" in required_dimensions
        and comparison.production_context_difference is ProductionContextDifference.UNKNOWN
    ):
        unresolved.append("production context")
    if "scope" in required_dimensions and comparison.scope_alignment is ScopeAlignment.UNKNOWN:
        unresolved.append("delivery scale")
    if "outcome" in required_dimensions and comparison.outcome_alignment is ScopeAlignment.UNKNOWN:
        unresolved.append("measurable outcomes")
    if unresolved:
        return comparison.model_copy(
            update={
                "match_type": None,
                "evidence_status": "UNKNOWN",
                "confidence": ConfidenceLevel.INSUFFICIENT,
                "clarification_needed": "Please provide a concrete example establishing "
                + ", ".join(unresolved)
                + ".",
            }
        )
    if (
        _requires_ownership(requirement)
        and comparison.ownership_alignment is OwnershipAlignment.UNKNOWN
    ):
        return comparison.model_copy(
            update={
                "match_type": None,
                "evidence_status": "UNKNOWN",
                "confidence": ConfidenceLevel.INSUFFICIENT,
                "clarification_needed": (
                    "What decisions did you personally own for "
                    f"{requirement.normalized_capability or requirement.requirement_text}?"
                ),
            }
        )
    supporting_ids = set(comparison.evidence_ids)
    supporting = [item for item in candidates if item.evidence_id in supporting_ids]
    if requirement.years_required is not None and requirement.relationship != "ANY_OF":
        years = [_explicit_years(item) for item in supporting]
        known_years = [value for value in years if value is not None]
        if not known_years:
            return comparison.model_copy(
                update={
                    "match_type": None,
                    "evidence_status": "UNKNOWN",
                    "confidence": ConfidenceLevel.INSUFFICIENT,
                    "clarification_needed": (
                        "How many years of directly relevant experience do you have for "
                        f"{requirement.normalized_capability or requirement.requirement_text}?"
                    ),
                    "validation_notes": [
                        *comparison.validation_notes,
                        "Required relevant years are not established by general tenure.",
                    ],
                }
            )
        if max(known_years) < requirement.years_required:
            return comparison.model_copy(
                update={
                    "match_type": MatchType.PARTIAL_MATCH,
                    "partial_match_subtype": PartialMatchSubtype.CAPABILITY_PRESENT_MATURITY_GAP,
                    "remaining_difference": (
                        f"Confirmed relevant experience ({max(known_years):g} years) is below the "
                        f"{requirement.years_required:g}-year requirement."
                    ),
                    "validation_notes": [
                        *comparison.validation_notes,
                        "Positive comparison corrected for confirmed years shortfall.",
                    ],
                }
            )
    descriptions = " ".join(
        " ".join(filter(None, [item.description, item.context, item.outcome]))
        for item in candidates
        if item.evidence_id in supporting_ids
    )
    if _requires_ownership(requirement) and (
        re.search(
            r"\b(?:did not|do not|never|not)\s+(?:personally\s+)?"
            r"(?:own|owned|manage|managed|lead|led)\b",
            descriptions,
            re.I,
        )
        or not _ownership_claim_supported(descriptions)
    ):
        return comparison.model_copy(
            update={
                "match_type": MatchType.PARTIAL_MATCH,
                "partial_match_subtype": PartialMatchSubtype.OWNERSHIP_OR_SCOPE_GAP,
                "ownership_alignment": OwnershipAlignment.PARTIAL,
                "remaining_difference": (
                    "Relevant work is demonstrated, but the target's personal ownership "
                    "is not established."
                ),
                "explanation": (
                    "Relevant contribution is present; required ownership is not confirmed."
                ),
                "validation_notes": [
                    *comparison.validation_notes,
                    "Positive match corrected because ownership lacked source support.",
                ],
            }
        )
    if (
        comparison.functional_overlap is not FunctionalOverlap.HIGH
        or comparison.ownership_alignment
        in {OwnershipAlignment.MISSING, OwnershipAlignment.PARTIAL}
        or comparison.scope_alignment in {ScopeAlignment.MISSING, ScopeAlignment.PARTIAL}
        or comparison.maturity_alignment is MaturityAlignment.BELOW_TARGET
        or comparison.production_context_difference
        in {
            ProductionContextDifference.PROJECT_TO_PRODUCTION,
            ProductionContextDifference.LIMITED_PRODUCTION_DEPTH,
            ProductionContextDifference.OTHER,
        }
        or comparison.outcome_alignment in {ScopeAlignment.PARTIAL, ScopeAlignment.MISSING}
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
            if comparison.ownership_alignment
            in {OwnershipAlignment.MISSING, OwnershipAlignment.PARTIAL}
            or comparison.scope_alignment in {ScopeAlignment.MISSING, ScopeAlignment.PARTIAL}
            else PartialMatchSubtype.ADJACENT_CAPABILITY_PARTIAL
        )
        return comparison.model_copy(
            update={
                "match_type": MatchType.PARTIAL_MATCH,
                "partial_match_subtype": subtype,
                "validation_notes": [
                    *comparison.validation_notes,
                    "Positive match corrected because a material dimensional difference remains.",
                ],
            }
        )
    return comparison


def compare_candidate_to_requirements(
    profile: CandidateProfile,
    analysis: MarketRequirementAnalysis,
    model_gateway: ModelGateway,
) -> CandidateComparisonResult:
    """Use factual checks for simple facts and semantic validation for complete expectations."""

    started = perf_counter()
    evidence = eligible_candidate_evidence(profile)
    scopes = _scope_by_posting(analysis)
    canonical_by_id = {
        item.canonical_requirement_id: item
        for item in (
            analysis.canonical_profile.comparison_requirements if analysis.canonical_profile else ()
        )
    }
    if analysis.canonical_profile is not None:
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
                comparison.model_copy(
                    update={
                        "source_requirement_ids": source_requirement_ids,
                        "selected_evidence_ids": [item.evidence_id for item in evidence],
                    }
                )
            )
            continue
        candidates = _candidate_set(requirement, evidence)
        cache_key = (
            scope,
            PROMPT_VERSION,
            json.dumps(
                requirement.model_dump(mode="json", exclude={"requirement_id", "posting_id"}),
                sort_keys=True,
            ),
            tuple(item.model_dump_json() for item in candidates),
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
                update={
                    "source_requirement_ids": source_requirement_ids,
                    "selected_evidence_ids": [item.evidence_id for item in candidates],
                    "omitted_evidence_ids": [
                        item.evidence_id for item in evidence if item not in candidates
                    ],
                }
            )
            comparisons.append(semantic_result)
            semantic_cache[cache_key] = semantic_result
            semantic_count += 1
        except (ModelGatewayError, TransferabilityAssessmentError, TypeError, ValueError) as error:
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
                evidence_status="OPERATION_FAILED",
                validation_notes=[f"Comparison stopped: {type(error).__name__}."],
                selected_evidence_ids=[item.evidence_id for item in candidates],
                omitted_evidence_ids=[
                    item.evidence_id for item in evidence if item not in candidates
                ],
            )
            comparisons.append(insufficient)
            semantic_cache[cache_key] = insufficient

    inspector = getattr(model_gateway, "inspector", None)
    if inspector is not None:
        for comparison in comparisons:
            inspector.record(
                "comparison_domain_validation",
                prompt_version=PROMPT_VERSION,
                comparison_id=str(comparison.comparison_id),
                requirement_id=str(comparison.requirement_id),
                source_requirement_ids=[str(value) for value in comparison.source_requirement_ids],
                selected_evidence_ids=[str(value) for value in comparison.selected_evidence_ids],
                omitted_evidence_ids=[str(value) for value in comparison.omitted_evidence_ids],
                validated_match=comparison.match_type.value if comparison.match_type else None,
                evidence_status=comparison.evidence_status,
                grounded_quote_count=len(comparison.grounded_evidence_quotes),
                validation_notes=comparison.validation_notes,
            )

    unknown_count = sum(item.match_type is None for item in comparisons)
    if unknown_count == len(comparisons):
        status = CandidateComparisonStatus.INSUFFICIENT_ANALYSIS
    elif failed_count or unknown_count:
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
