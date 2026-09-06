"""Deterministic canonical target-role profile over posting-level requirements."""

import re
from collections import Counter
from datetime import datetime

from ai_career_navigator.domain import (
    ConfidenceLevel,
    EvidenceMaturity,
    RequirementCategory,
    RequirementFrequency,
    RequirementStatementType,
    RoleRequirement,
)

from .requirement_schemas import (
    CanonicalRequirementKind,
    CanonicalRequirementScope,
    CanonicalRoleRequirement,
    CanonicalTargetRoleProfile,
    MarketRequirementSummary,
    PostingCandidateAssessment,
    PostingRequirementAudit,
    PostingTitleMatch,
    RoleProfileStatus,
)
from .schemas import MarketSourceProvider, SourceAgreement

STABLE_PRIMARY_POSTING_MIN = 5
STABLE_PRIMARY_EMPLOYER_MIN = 3
PROVISIONAL_PRIMARY_POSTING_MIN = 2
CORE_SUPPORT_RATIO = 0.50
SECONDARY_SUPPORT_RATIO = 0.30
COMMON_SUPPORT_RATIO = 0.60
FREQUENT_SUPPORT_RATIO = 0.35
OCCASIONAL_SUPPORT_RATIO = 0.15

_PRIMARY = {PostingTitleMatch.EXACT_TARGET, PostingTitleMatch.TARGET_VARIANT}
_PREREQUISITES = {
    RequirementCategory.EDUCATION,
    RequirementCategory.CREDENTIAL,
    RequirementCategory.WORK_AUTHORIZATION,
    RequirementCategory.LANGUAGE,
    RequirementCategory.LOCATION,
}
_MATURITY_RANK = {value: index for index, value in enumerate(EvidenceMaturity)}
_CONFIDENCE_RANK = {value: index for index, value in enumerate(reversed(ConfidenceLevel))}
_TOKEN_ALIASES = {
    "architecting": "architecture",
    "architectural": "architecture",
    "collaborating": "collaboration",
    "collaborate": "collaboration",
    "communication": "collaboration",
    "communications": "collaboration",
    "leading": "leadership",
    "lead": "leadership",
    "management": "management",
    "managing": "management",
    "partnership": "collaboration",
    "partnering": "collaboration",
    "owned": "ownership",
    "own": "ownership",
    "prioritization": "ownership",
    "prioritizing": "ownership",
    "roadmaps": "roadmap",
    "solutions": "solution",
    "products": "product",
    "designing": "design",
    "designed": "design",
    "scalable": "scaling",
    "scale": "scaling",
    "scaled": "scaling",
    "stakeholders": "stakeholder",
}
_CONCEPT_EXPANSIONS = {
    "aws": {"amazon", "web", "services", "cloud"},
    "genai": {"generative", "artificial", "intelligence", "ai"},
    "llm": {"large", "language", "model"},
    "llms": {"large", "language", "model"},
    "rag": {"retrieval", "augmented", "generation"},
}
_LOW_INFORMATION = {
    "and",
    "for",
    "the",
    "with",
    "ability",
    "experience",
    "knowledge",
    "skills",
    "strong",
}
_SHORT_MEANINGFUL_TOKENS = {"ai", "ci", "cd", "c#"}


def _tokens(value: str) -> set[str]:
    return {
        _TOKEN_ALIASES.get(token, token)
        for token in re.findall(r"[a-z0-9+#.]+", value.casefold())
        if token not in _LOW_INFORMATION and (len(token) > 2 or token in _SHORT_MEANINGFUL_TOKENS)
    }


def quote_capability_alignment(quote: str, capability: str) -> tuple[bool, str | None]:
    """Reject clearly unrelated quote-to-capability mappings; leave ambiguity explicit."""

    quote_tokens = _tokens(quote)
    capability_tokens = _tokens(capability)
    if not capability_tokens:
        return False, "Normalized capability has no meaningful semantic tokens."
    overlap = quote_tokens & capability_tokens
    if overlap:
        return True, None
    if any(
        expansion & quote_tokens
        for token, expansion in _CONCEPT_EXPANSIONS.items()
        if token in capability_tokens
    ):
        return True, None
    return (
        False,
        "Normalized capability has no lexical or configured semantic overlap "
        "with its source quote.",
    )


def _semantic_key(requirement: RoleRequirement) -> tuple[str, str]:
    name = requirement.normalized_capability or requirement.requirement_text
    tokens = _tokens(name)
    if "stakeholder" in tokens and tokens & {"collaboration", "management"}:
        concept = "stakeholder collaboration"
    elif "roadmap" in tokens and tokens & {"ownership", "management"}:
        concept = "roadmap ownership"
    else:
        concept = " ".join(sorted(tokens))
    category_group = (
        "prerequisite"
        if requirement.category in _PREREQUISITES
        else "stakeholder"
        if concept == "stakeholder collaboration"
        else requirement.category.value
    )
    return category_group, concept


def _display_name(requirements: list[RoleRequirement], key: tuple[str, str]) -> str:
    if key[1] == "stakeholder collaboration":
        return "Stakeholder Collaboration"
    if key[1] == "roadmap ownership":
        return "Roadmap Ownership"
    names = [
        requirement.normalized_capability or requirement.requirement_text
        for requirement in requirements
    ]
    counts = Counter(names)
    return min(counts, key=lambda value: (-counts[value], len(value), value.casefold()))[:120]


def _frequency(value: float) -> RequirementFrequency:
    if value >= COMMON_SUPPORT_RATIO:
        return RequirementFrequency.COMMON
    if value >= FREQUENT_SUPPORT_RATIO:
        return RequirementFrequency.FREQUENT
    if value >= OCCASIONAL_SUPPORT_RATIO:
        return RequirementFrequency.OCCASIONAL
    return RequirementFrequency.RARE


def _support_identity(assessment: PostingCandidateAssessment) -> str:
    employer = " ".join((assessment.candidate.employer or "").casefold().split())
    return f"employer:{employer}" if employer else f"posting:{assessment.candidate.posting_id}"


def _kind(requirements: list[RoleRequirement]) -> CanonicalRequirementKind:
    statement_types = {item.statement_type for item in requirements}
    if statement_types == {RequirementStatementType.ROLE_RESPONSIBILITY}:
        return CanonicalRequirementKind.ROLE_RESPONSIBILITY
    if statement_types == {RequirementStatementType.PREFERENCE}:
        return CanonicalRequirementKind.PREFERENCE
    category = Counter(item.category for item in requirements).most_common(1)[0][0]
    if category in _PREREQUISITES:
        return CanonicalRequirementKind.PREREQUISITE
    if category is RequirementCategory.EXPERIENCE or any(
        item.years_required is not None for item in requirements
    ):
        return CanonicalRequirementKind.EXPERIENCE_THRESHOLD
    return CanonicalRequirementKind.CAPABILITY


def build_canonical_target_role_profile(
    *,
    target_role: str,
    geography: str,
    requirements: list[RoleRequirement],
    assessments: list[PostingCandidateAssessment],
    summary: MarketRequirementSummary,
    posting_audits: list[PostingRequirementAudit],
    generated_at: datetime,
) -> tuple[CanonicalTargetRoleProfile, list[PostingRequirementAudit]]:
    """Consolidate primary requirements and retain related-only observations separately."""

    assessment_by_posting = {
        item.candidate.posting_id: item
        for item in assessments
        if item.geography_status.value == "IN_SCOPE"
        and item.title_match is not PostingTitleMatch.IRRELEVANT
    }
    analyzed_posting_ids = {
        audit.posting_id for audit in posting_audits if audit.extraction_status.value == "SUCCEEDED"
    }
    analyzed_assessments = [
        item
        for posting_id, item in assessment_by_posting.items()
        if posting_id in analyzed_posting_ids
    ]
    primary_assessments = [item for item in analyzed_assessments if item.title_match in _PRIMARY]
    primary_identities = {_support_identity(item) for item in primary_assessments}
    primary_denominator = len(primary_identities)
    exact_employers = {
        " ".join(item.candidate.employer.casefold().split())
        for item in primary_assessments
        if item.title_match is PostingTitleMatch.EXACT_TARGET and item.candidate.employer
    }
    variant_employers = {
        " ".join(item.candidate.employer.casefold().split())
        for item in primary_assessments
        if item.title_match is PostingTitleMatch.TARGET_VARIANT and item.candidate.employer
    }

    grouped: dict[tuple[str, str], list[RoleRequirement]] = {}
    for requirement in requirements:
        grouped.setdefault(_semantic_key(requirement), []).append(requirement)

    canonical: list[CanonicalRoleRequirement] = []
    source_to_canonical = {}
    for key, items in grouped.items():
        responsibility_items = [
            item
            for item in items
            if item.statement_type is RequirementStatementType.ROLE_RESPONSIBILITY
        ]
        preference_items = [
            item for item in items if item.statement_type is RequirementStatementType.PREFERENCE
        ]
        qualification_items = [
            item
            for item in items
            if item.statement_type
            in {
                RequirementStatementType.HIRING_CAPABILITY,
                RequirementStatementType.PREREQUISITE,
            }
        ]
        basis_items = qualification_items or responsibility_items or preference_items
        supporting_assessments = [
            assessment_by_posting[item.posting_id]
            for item in basis_items
            if item.posting_id in assessment_by_posting
        ]
        exact_ids = {
            item.candidate.posting_id
            for item in supporting_assessments
            if item.title_match is PostingTitleMatch.EXACT_TARGET
        }
        variant_ids = {
            item.candidate.posting_id
            for item in supporting_assessments
            if item.title_match is PostingTitleMatch.TARGET_VARIANT
        }
        related_ids = {
            item.candidate.posting_id
            for item in supporting_assessments
            if item.title_match is PostingTitleMatch.RELATED_TITLE
        }
        primary_support = exact_ids | variant_ids
        supporting_identities = {
            _support_identity(item)
            for item in supporting_assessments
            if item.title_match in _PRIMARY
        }
        ratio = len(supporting_identities) / primary_denominator if primary_denominator else 0
        mandatory_signal = bool(primary_support) and (
            len(
                {
                    item.posting_id
                    for item in qualification_items
                    if item.posting_id in primary_support and item.mandatory
                }
            )
            / len(primary_support)
            >= 0.5
        )
        preferred_signal = not mandatory_signal and any(
            item.preferred and item.posting_id in primary_support
            for item in [*qualification_items, *preference_items]
        )
        kind = _kind(basis_items)
        if not primary_support:
            scope = CanonicalRequirementScope.OPTIONAL
        elif kind in {
            CanonicalRequirementKind.ROLE_RESPONSIBILITY,
            CanonicalRequirementKind.PREFERENCE,
        }:
            scope = CanonicalRequirementScope.OPTIONAL
        elif kind is CanonicalRequirementKind.PREREQUISITE:
            scope = CanonicalRequirementScope.PREREQUISITE
        elif len(supporting_identities) >= 2 and ratio >= CORE_SUPPORT_RATIO:
            scope = CanonicalRequirementScope.CORE
        elif ratio >= SECONDARY_SUPPORT_RATIO or (
            mandatory_signal and len(supporting_identities) >= 2
        ):
            scope = CanonicalRequirementScope.SECONDARY
        else:
            scope = CanonicalRequirementScope.OPTIONAL
        category = Counter(item.category for item in basis_items).most_common(1)[0][0]
        maturities = [item.maturity_expected for item in basis_items if item.maturity_expected]
        confidences = [item.extraction_confidence for item in items]
        employers = list(
            dict.fromkeys(
                item.candidate.employer
                for item in supporting_assessments
                if item.candidate.employer
            )
        )
        primary_employers = {
            " ".join(item.candidate.employer.casefold().split())
            for item in supporting_assessments
            if item.title_match in _PRIMARY and item.candidate.employer
        }
        exact_supporting_employers = {
            " ".join(item.candidate.employer.casefold().split())
            for item in supporting_assessments
            if item.title_match is PostingTitleMatch.EXACT_TARGET and item.candidate.employer
        }
        variant_supporting_employers = {
            " ".join(item.candidate.employer.casefold().split())
            for item in supporting_assessments
            if item.title_match is PostingTitleMatch.TARGET_VARIANT and item.candidate.employer
        }
        posting_ids = [*sorted(primary_support, key=str), *sorted(related_ids, key=str)]
        all_supporting_assessments = [
            assessment_by_posting[item.posting_id]
            for item in items
            if item.posting_id in assessment_by_posting
        ]
        responsibility_posting_ids = {
            item.posting_id
            for item in responsibility_items
            if item.posting_id in assessment_by_posting
        }
        qualification_posting_ids = {
            item.posting_id
            for item in qualification_items
            if item.posting_id in assessment_by_posting
        }
        adzuna_ids = {
            item.candidate.posting_id
            for item in supporting_assessments
            if item.title_match in _PRIMARY
            if MarketSourceProvider.ADZUNA.value
            in (item.candidate.provider_sources or [item.candidate.provider or ""])
        }
        you_ids = {
            item.candidate.posting_id
            for item in supporting_assessments
            if item.title_match in _PRIMARY
            if MarketSourceProvider.YOU.value
            in (item.candidate.provider_sources or [item.candidate.provider or ""])
        }
        if adzuna_ids and you_ids and len(primary_employers) >= 2:
            source_agreement = SourceAgreement.CROSS_SOURCE_CONFIRMED
        elif len(primary_employers) >= 2:
            source_agreement = SourceAgreement.SINGLE_SOURCE_SUPPORTED
        else:
            source_agreement = SourceAgreement.LOW_SUPPORT
        canonical_item = CanonicalRoleRequirement(
            display_name=_display_name(items, key),
            category=category,
            requirement_kind=kind,
            expected_maturity=(
                max(maturities, key=lambda value: _MATURITY_RANK[value]) if maturities else None
            ),
            mandatory_signal=mandatory_signal,
            preferred_signal=preferred_signal,
            frequency_band=_frequency(ratio),
            primary_support_ratio=ratio,
            employer_support_count=len(primary_employers),
            exact_employer_support_count=len(exact_supporting_employers),
            variant_employer_support_count=len(variant_supporting_employers),
            posting_support_count=len(set(posting_ids)),
            responsibility_support_count=len(responsibility_posting_ids),
            qualification_support_count=len(qualification_posting_ids),
            exact_support_count=len(exact_ids),
            variant_support_count=len(variant_ids),
            related_support_count=len(related_ids),
            adzuna_support_count=len(adzuna_ids),
            you_support_count=len(you_ids),
            source_agreement=source_agreement,
            supporting_requirement_ids=[item.requirement_id for item in items],
            responsibility_requirement_ids=[
                item.requirement_id for item in responsibility_items
            ],
            qualification_requirement_ids=[
                item.requirement_id for item in qualification_items
            ],
            supporting_posting_ids=posting_ids,
            supporting_employers=employers,
            provider_sources=list(
                dict.fromkeys(
                    MarketSourceProvider(provider)
                    for assessment in all_supporting_assessments
                    for provider in (
                        assessment.candidate.provider_sources
                        or (
                            [assessment.candidate.provider]
                            if assessment.candidate.provider
                            else []
                        )
                    )
                    if provider in {item.value for item in MarketSourceProvider}
                )
            ),
            source_provenance=list(
                dict.fromkeys(
                    source
                    for assessment in all_supporting_assessments
                    for source in (
                        assessment.candidate.source_provenance
                        or [
                            assessment.candidate.source_url
                            or assessment.candidate.source_reference
                        ]
                    )
                )
            ),
            statement_types=list(dict.fromkeys(item.statement_type for item in items)),
            representative_source_quotes=list(
                dict.fromkeys(
                    item.requirement_text
                    for item in [
                        *qualification_items,
                        *responsibility_items,
                        *preference_items,
                    ]
                )
            )[:3],
            confidence=min(confidences, key=lambda value: _CONFIDENCE_RANK[value]),
            requirement_scope=scope,
        )
        canonical.append(canonical_item)
        source_to_canonical.update(
            {item.requirement_id: canonical_item.canonical_requirement_id for item in items}
        )

    primary_items = [
        item
        for item in canonical
        if item.requirement_scope is not CanonicalRequirementScope.OPTIONAL
        and item.requirement_kind
        not in {
            CanonicalRequirementKind.ROLE_RESPONSIBILITY,
            CanonicalRequirementKind.PREFERENCE,
        }
    ]
    repeated = sum(item.employer_support_count >= 2 for item in primary_items)
    agreement = repeated / len(primary_items) if primary_items else 0
    extraction_success_rate = (
        summary.analyzed_posting_count / summary.validated_in_scope_posting_count
        if summary.validated_in_scope_posting_count
        else 0
    )
    primary_providers = {
        provider
        for assessment in primary_assessments
        for provider in (
            assessment.candidate.provider_sources
            or ([assessment.candidate.provider] if assessment.candidate.provider else [])
        )
    }
    high_quality_ratio = (
        sum(
            item.candidate.retrieval_quality in {None, "HIGH"}
            for item in primary_assessments
        )
        / len(primary_assessments)
        if primary_assessments
        else 0
    )
    usable_primary_posting_ids = {
        posting_id
        for item in primary_items
        for posting_id in item.supporting_posting_ids
        if posting_id in assessment_by_posting
        and assessment_by_posting[posting_id].title_match in _PRIMARY
    }
    usable_primary_identities = {
        _support_identity(assessment_by_posting[posting_id])
        for posting_id in usable_primary_posting_ids
    }
    usable_exact_identities = {
        _support_identity(assessment_by_posting[posting_id])
        for posting_id in usable_primary_posting_ids
        if assessment_by_posting[posting_id].title_match is PostingTitleMatch.EXACT_TARGET
    }
    if len(usable_primary_identities) < PROVISIONAL_PRIMARY_POSTING_MIN or not primary_items:
        status = RoleProfileStatus.INSUFFICIENT
        confidence = ConfidenceLevel.INSUFFICIENT
    elif (
        len(primary_assessments) >= STABLE_PRIMARY_POSTING_MIN
        and len(primary_identities) >= STABLE_PRIMARY_EMPLOYER_MIN
        and len(usable_exact_identities) >= STABLE_PRIMARY_EMPLOYER_MIN
        and agreement >= 0.5
        and extraction_success_rate >= 0.7
        and high_quality_ratio >= 0.5
    ):
        status = RoleProfileStatus.STABLE
        confidence = ConfidenceLevel.HIGH
    else:
        status = RoleProfileStatus.PROVISIONAL
        confidence = (
            ConfidenceLevel.MODERATE
            if len(primary_assessments) >= 3
            and len(primary_identities) >= 2
            and len(usable_exact_identities) >= 2
            and agreement >= 0.25
            and extraction_success_rate >= 0.5
            and (len(primary_providers) >= 2 or len(primary_assessments) >= 4)
            else ConfidenceLevel.LOW
        )

    limitations = []
    if status is RoleProfileStatus.PROVISIONAL:
        limitations.append(
            "The canonical role profile is provisional because exact/variant evidence is sparse."
        )
    elif status is RoleProfileStatus.INSUFFICIENT:
        limitations.append(
            "There is not enough exact/variant evidence to form a defensible target-role profile."
        )
    profile = CanonicalTargetRoleProfile(
        target_role=target_role,
        geography=geography,
        profile_status=status,
        confidence=confidence,
        exact_posting_count=sum(
            item.title_match is PostingTitleMatch.EXACT_TARGET
            for item in assessment_by_posting.values()
        ),
        variant_posting_count=sum(
            item.title_match is PostingTitleMatch.TARGET_VARIANT
            for item in assessment_by_posting.values()
        ),
        related_posting_count=sum(
            item.title_match is PostingTitleMatch.RELATED_TITLE
            for item in assessment_by_posting.values()
        ),
        distinct_exact_employer_count=len(exact_employers),
        distinct_variant_employer_count=len(variant_employers),
        analyzed_exact_posting_count=summary.exact_title_analyzed_count,
        analyzed_variant_posting_count=summary.target_variant_analyzed_count,
        analyzed_related_posting_count=summary.related_title_analyzed_count,
        generated_at=generated_at,
        requirements=[
            item
            for item in canonical
            if item.requirement_scope
            in {CanonicalRequirementScope.CORE, CanonicalRequirementScope.SECONDARY}
        ],
        responsibilities=[
            item
            for item in canonical
            if item.responsibility_support_count
            and item.exact_support_count + item.variant_support_count
        ],
        prerequisites=[
            item
            for item in canonical
            if item.requirement_scope is CanonicalRequirementScope.PREREQUISITE
        ],
        preferences=[
            item
            for item in canonical
            if RequirementStatementType.PREFERENCE in item.statement_types
            and item.exact_support_count + item.variant_support_count
        ],
        optional_signals=[
            item
            for item in canonical
            if item.requirement_scope is CanonicalRequirementScope.OPTIONAL
            and item.exact_support_count + item.variant_support_count
            and item.requirement_kind
            not in {
                CanonicalRequirementKind.ROLE_RESPONSIBILITY,
                CanonicalRequirementKind.PREFERENCE,
            }
        ],
        related_context=[
            item
            for item in canonical
            if not item.exact_support_count and not item.variant_support_count
        ],
        limitations=limitations,
    )
    source_statement_type = {
        item.requirement_id: item.statement_type for item in requirements
    }
    canonical_classification_by_source = {
        source_id: (
            source_statement_type[source_id].value
            if source_statement_type.get(source_id)
            in {
                RequirementStatementType.ROLE_RESPONSIBILITY,
                RequirementStatementType.PREFERENCE,
            }
            else item.requirement_scope.value
        )
        for item in canonical
        for source_id in item.supporting_requirement_ids
    }
    updated_audits = []
    for audit in posting_audits:
        updated_audits.append(
            audit.model_copy(
                update={
                    "items": [
                        item.model_copy(
                            update={
                                "canonical_requirement_id": source_to_canonical.get(
                                    item.source_requirement_id
                                ),
                                "final_classification": (
                                    canonical_classification_by_source.get(
                                        item.source_requirement_id,
                                        item.final_classification,
                                    )
                                    if item.accepted
                                    else item.final_classification
                                ),
                            }
                        )
                        for item in audit.items
                    ]
                }
            )
        )
    return profile, updated_audits
