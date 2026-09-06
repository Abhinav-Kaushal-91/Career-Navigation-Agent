"""Posting-level requirement extraction and exact/related-aware aggregation."""

import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime

from ai_career_navigator.domain import (
    ConfidenceLevel,
    JobPosting,
    RequirementCategory,
    RequirementStatementType,
    RoleRequirement,
)
from ai_career_navigator.market.normalization import normalize_employer, normalize_title
from ai_career_navigator.market.processing import (
    assess_candidate,
    assess_title,
    classify_and_segment_source,
)
from ai_career_navigator.market.requirement_prompts import (
    PROMPT_VERSION,
    REQUIREMENT_SYSTEM_PROMPT,
    build_requirement_prompt,
)
from ai_career_navigator.market.requirement_schemas import (
    AggregatedRequirement,
    ExtractedRequirement,
    MarketRequirementAnalysis,
    MarketRequirementSummary,
    PostingCandidate,
    PostingCandidateAssessment,
    PostingExtractionQuality,
    PostingGeographyStatus,
    PostingRequirementAudit,
    PostingRequirementAuditItem,
    PostingRequirementResult,
    PostingTitleMatch,
    RequirementAuditStatus,
    RequirementItemType,
    RequirementRunStatus,
    RoleProfileStatus,
    SeniorityAlignment,
    TargetVariantAssessmentResult,
    TargetVariantAudit,
    TargetVariantClassification,
)
from ai_career_navigator.market.role_profile import (
    build_canonical_target_role_profile,
    quote_capability_alignment,
)
from ai_career_navigator.market.schemas import (
    EnrichmentStatus,
    MarketPostingEvidence,
    PostingSourceType,
    RetainedSourceContent,
)
from ai_career_navigator.market.variant_prompts import (
    PROMPT_VERSION as VARIANT_PROMPT_VERSION,
)
from ai_career_navigator.market.variant_prompts import (
    SYSTEM_PROMPT as VARIANT_SYSTEM_PROMPT,
)
from ai_career_navigator.market.variant_prompts import (
    build_variant_prompt,
)
from ai_career_navigator.models import ModelGateway, ModelGatewayError, ModelRole

logger = logging.getLogger(__name__)

CANONICAL_ALIASES = {
    "microsoft azure": "Azure",
    "azure cloud": "Azure",
    "azure": "Azure",
    "amazon web services": "AWS",
    "aws": "AWS",
    "large language model": "LLMs",
    "large language models": "LLMs",
    "llm": "LLMs",
    "llms": "LLMs",
    "generative ai": "GenAI",
    "genai": "GenAI",
    "retrieval augmented generation": "RAG",
    "rag": "RAG",
    "ci cd": "CI/CD",
    "rest api": "REST APIs",
    "rest apis": "REST APIs",
    "rest api s": "REST APIs",
}
PREREQUISITE_CATEGORIES = {
    RequirementCategory.EDUCATION,
    RequirementCategory.CREDENTIAL,
    RequirementCategory.LOCATION,
    RequirementCategory.WORK_AUTHORIZATION,
    RequirementCategory.LANGUAGE,
}
METADATA_PATTERN = re.compile(
    r"(?:\$\s?\d|salary|compensation|benefits?|"
    r"\b\d+[- ]months?\b.*\bcontract\b|\bcontract\b.*\b\d+[- ]months?\b|"
    r"\bjob type\b|\bfull[- ]time position\b|\bpart[- ]time position\b|"
    r"\bfull[- ]?time\b|\bpart[- ]?time\b|\bhome office\b|\bwork from home\b|"
    r"\bhybrid work\b|\bremote work\b|\bonsite\b|\bon-site\b|"
    r"\bprimary location\b|\ball available locations\b|^\s*location\s*:)",
    re.IGNORECASE,
)
QUALIFICATION_PATTERN = re.compile(
    r"\b(?:must|required|requirement|experience|years?|proficien|knowledge|expertise|"
    r"degree|certif|authorization|eligible|ability|skills?|qualification|candidate)\b",
    re.IGNORECASE,
)
RESPONSIBILITY_PATTERN = re.compile(
    r"^(?:(?:you (?:will|would)\s+|responsible for\s+)?(?:design|build|develop|"
    r"implement|lead|manage|create|deliver|architect|collaborate|"
    r"own|define|drive|conduct|support|monitor|partner|oversee|establish|coordinate))\b",
    re.IGNORECASE,
)
GENERIC_DESCRIPTION_PATTERN = re.compile(
    r"\b(?:role with|opportunity with|join our|global organization|about (?:us|the company)|"
    r"we are (?:seeking|looking for)|this role|responsible for|you will|"
    r"plays a hands-on role|ready to|push the limits|what(?:'|’)?s possible)\b",
    re.IGNORECASE,
)
SELF_IDENTIFIED_ROLE_PATTERN = re.compile(
    r"(?:^|[.!?]\s+)as\s+an?\s+([a-z][a-z0-9 /&+\-]{2,70}?),?\s+you\b",
    re.IGNORECASE,
)
GENERIC_TITLE_TOKENS = {
    "assistant",
    "associate",
    "director",
    "head",
    "junior",
    "lead",
    "manager",
    "principal",
    "senior",
    "specialist",
}
MAX_VARIANT_CANDIDATE_TITLES = 5
MAX_VARIANT_POSTINGS = 5
VARIANT_OVERLAP_MINIMUM = 0.7


@dataclass(frozen=True)
class _ExtractionOutcome:
    requirements: list[RoleRequirement]
    limitations: list[str]
    raw_count: int
    capability_count: int
    responsibility_count: int
    preference_count: int
    prerequisite_count: int
    rejected_count: int
    unsupported_count: int
    audit_items: list[PostingRequirementAuditItem]
    failure_category: str | None = None


def canonical_capability(value: str) -> str:
    key = normalize_requirement(value.replace("/", " ").replace("-", " "))
    return CANONICAL_ALIASES.get(key, " ".join(value.split()).strip())


def _is_concise_capability(value: str) -> bool:
    return bool(value) and len(value) <= 80 and len(value.split()) <= 8


def _is_role_label_restatement(value: str, title: str) -> bool:
    aliases = {
        "engineering": "engineer",
        "management": "manager",
        "development": "developer",
        "architecture": "architect",
        "analysis": "analyst",
        "solutions": "solution",
    }

    def tokens(text: str) -> set[str]:
        return {
            aliases.get(token, token)
            for token in normalize_requirement(text).split()
            if token not in GENERIC_TITLE_TOKENS
        }

    observed = tokens(value)
    target = tokens(title)
    return bool(observed) and observed == target


def _item_group(item: ExtractedRequirement) -> RequirementItemType:
    if item.item_type is RequirementItemType.METADATA_NON_REQUIREMENT:
        return RequirementItemType.METADATA_NON_REQUIREMENT
    if METADATA_PATTERN.search(item.source_quote) or METADATA_PATTERN.search(
        item.normalized_capability or ""
    ):
        return RequirementItemType.METADATA_NON_REQUIREMENT
    if item.category in PREREQUISITE_CATEGORIES:
        return RequirementItemType.PREREQUISITE
    if item.item_type is RequirementItemType.PREREQUISITE:
        return RequirementItemType.PREREQUISITE
    if item.item_type is RequirementItemType.PREFERENCE or item.preferred:
        return RequirementItemType.PREFERENCE
    is_responsibility = RESPONSIBILITY_PATTERN.search(item.source_quote.strip())
    if is_responsibility and not QUALIFICATION_PATTERN.search(item.source_quote):
        return RequirementItemType.ROLE_RESPONSIBILITY
    if item.item_type is RequirementItemType.ROLE_RESPONSIBILITY:
        return RequirementItemType.ROLE_RESPONSIBILITY
    if (
        GENERIC_DESCRIPTION_PATTERN.search(item.source_quote)
        or GENERIC_DESCRIPTION_PATTERN.search(item.normalized_capability or "")
    ) and not QUALIFICATION_PATTERN.search(item.source_quote):
        return RequirementItemType.METADATA_NON_REQUIREMENT
    return RequirementItemType.HIRING_CAPABILITY


def _statement_type(group: RequirementItemType) -> RequirementStatementType:
    return {
        RequirementItemType.ROLE_RESPONSIBILITY: RequirementStatementType.ROLE_RESPONSIBILITY,
        RequirementItemType.HIRING_CAPABILITY: RequirementStatementType.HIRING_CAPABILITY,
        RequirementItemType.PREREQUISITE: RequirementStatementType.PREREQUISITE,
        RequirementItemType.PREFERENCE: RequirementStatementType.PREFERENCE,
    }[group]


def normalize_requirement(value: str) -> str:
    """Use narrow textual normalization, not semantic ontology matching."""

    return " ".join(re.findall(r"[a-z0-9+#.]+", value.casefold()))


def _contains_quote(quote: str, text: str) -> bool:
    return " ".join(quote.split()).casefold() in " ".join(text.split()).casefold()


def _body_title_mismatch(title: str, posting_text: str) -> str | None:
    """Return a conflicting self-identified role when the body states one clearly."""

    match = SELF_IDENTIFIED_ROLE_PATTERN.search(posting_text[:4000])
    if not match:
        return None
    body_role = " ".join(match.group(1).split())
    title_tokens = set(normalize_requirement(title).split()) - GENERIC_TITLE_TOKENS
    body_tokens = set(normalize_requirement(body_role).split()) - GENERIC_TITLE_TOKENS
    if title_tokens and body_tokens and not title_tokens & body_tokens:
        return body_role
    return None


def _posting(candidate: PostingCandidate, *, retrieved_at: datetime) -> JobPosting:
    return JobPosting(
        posting_id=candidate.posting_id,
        source_id=candidate.source_id,
        original_title=candidate.title,
        normalized_title=normalize_title(candidate.title),
        employer=normalize_employer(candidate.employer),
        location=candidate.location,
        location_evidence_text=candidate.location_evidence_text,
        retrieved_at=retrieved_at,
        active_status="OBSERVED",
        extraction_confidence=candidate.extraction_confidence,
    )


def _deduplicate_assessments(
    assessments: list[PostingCandidateAssessment],
) -> list[PostingCandidateAssessment]:
    retained: dict[tuple[str, str, str], PostingCandidateAssessment] = {}
    for assessment in assessments:
        candidate = assessment.candidate
        key = (
            normalize_requirement(candidate.title),
            normalize_requirement(candidate.employer or ""),
            normalize_requirement(candidate.location or ""),
        )
        retained.setdefault(key, assessment)
    return list(retained.values())


def _assessment_from_evidence(
    evidence: MarketPostingEvidence,
    *,
    target_role: str,
) -> PostingCandidateAssessment | None:
    """Adapt an already-validated structured posting without segmenting it again."""

    if evidence.source_type is PostingSourceType.BACKGROUND_CONTEXT:
        return None
    posting = evidence.posting
    text = evidence.primary_content.markdown.strip()
    if not text:
        return None
    candidate = PostingCandidate(
        posting_id=posting.posting_id,
        source_id=posting.source_id,
        source_reference=" > ".join(
            part
            for part in (
                evidence.primary_source.title,
                posting.employer,
                posting.original_title,
            )
            if part
        ),
        source_reference_text=" ".join(
            part
            for part in (
                posting.original_title,
                posting.employer,
                posting.location,
            )
            if part
        ),
        title=posting.original_title,
        employer=posting.employer,
        location=posting.location,
        location_evidence_text=posting.location_evidence_text,
        posting_text=text[:20_000],
        extraction_confidence=posting.extraction_confidence,
        provider=evidence.primary_source.source_type,
        provider_sources=[item.value for item in evidence.provider_sources],
        source_type=evidence.source_type.value,
        source_url=str(evidence.primary_source.url),
        source_provenance=list(
            dict.fromkeys(
                str(source.url)
                for source in [evidence.primary_source, *evidence.supporting_sources]
            )
        ),
        retrieval_quality=evidence.retrieval_quality.value,
        seniority_classification=evidence.seniority_classification.value,
        selected_content_source=(
            evidence.selected_content_source.value if evidence.selected_content_source else None
        ),
        title_classification=evidence.title_classification,
        posting_date=posting.posting_date,
    )
    return PostingCandidateAssessment(
        candidate=candidate,
        geography_status=PostingGeographyStatus.IN_SCOPE,
        geography_evidence_text=posting.location_evidence_text,
        requested_geography_scope=posting.requested_geography_scope,
        matched_geography_scope=posting.matched_geography_scope,
        title_match=(
            PostingTitleMatch(evidence.title_classification)
            if evidence.title_classification
            else assess_title(posting.original_title, target_role)
        ),
    )


def _scope_order(assessment: PostingCandidateAssessment) -> int:
    return {
        PostingTitleMatch.EXACT_TARGET: 0,
        PostingTitleMatch.TARGET_VARIANT: 1,
        PostingTitleMatch.RELATED_TITLE: 2,
        PostingTitleMatch.IRRELEVANT: 3,
    }[assessment.title_match]


def _select_employer_diverse(
    assessments: list[PostingCandidateAssessment], limit: int
) -> list[PostingCandidateAssessment]:
    """Select bounded posting evidence without allowing one employer to dominate."""

    remaining = list(assessments)
    selected: list[PostingCandidateAssessment] = []
    employers: set[str] = set()
    providers: set[str] = set()
    quality_rank = {"HIGH": 2, "MODERATE": 1, "LOW": 0, None: 0}
    title_rank = {
        PostingTitleMatch.EXACT_TARGET: 3,
        PostingTitleMatch.TARGET_VARIANT: 2,
        PostingTitleMatch.RELATED_TITLE: 1,
        PostingTitleMatch.IRRELEVANT: 0,
    }
    while remaining and len(selected) < limit:
        remaining.sort(
            key=lambda item: (
                title_rank[item.title_match],
                int(item.candidate.seniority_classification in {None, "STANDARD"}),
                int(
                    (normalize_employer(item.candidate.employer) or "").casefold()
                    not in employers
                ),
                quality_rank.get(item.candidate.retrieval_quality, 0),
                len(item.candidate.posting_text),
                int(item.candidate.posting_date is not None),
                int(any(value not in providers for value in item.candidate.provider_sources)),
            ),
            reverse=True,
        )
        chosen = remaining.pop(0)
        selected.append(chosen)
        employer = (normalize_employer(chosen.candidate.employer) or "").casefold()
        if employer:
            employers.add(employer)
        providers.update(chosen.candidate.provider_sources)
    return selected


def _quality_and_audit(
    assessment: PostingCandidateAssessment,
    outcome: _ExtractionOutcome,
    *,
    enrichment_used: bool,
) -> tuple[PostingExtractionQuality, PostingRequirementAudit]:
    candidate = assessment.candidate
    return (
        PostingExtractionQuality(
            posting_id=candidate.posting_id,
            source_id=candidate.source_id,
            title=candidate.title,
            employer=candidate.employer,
            input_description_characters=len(candidate.posting_text),
            enrichment_used=enrichment_used,
            raw_extracted_item_count=outcome.raw_count,
            accepted_capability_requirement_count=outcome.capability_count,
            accepted_role_responsibility_count=outcome.responsibility_count,
            accepted_preference_count=outcome.preference_count,
            prerequisite_condition_count=outcome.prerequisite_count,
            rejected_metadata_non_requirement_count=outcome.rejected_count,
            unsupported_grounding_count=outcome.unsupported_count,
            failure_category=outcome.failure_category,
            limitations=outcome.limitations,
        ),
        PostingRequirementAudit(
            posting_id=candidate.posting_id,
            title=candidate.title,
            employer=candidate.employer,
            location=candidate.location,
            title_classification=assessment.title_match,
            provider=candidate.provider,
            source_reference=candidate.source_reference,
            extraction_status=(
                RequirementAuditStatus.FAILED
                if outcome.failure_category
                else RequirementAuditStatus.SUCCEEDED
            ),
            items=outcome.audit_items,
        ),
    )


def extract_posting_requirements(
    assessment: PostingCandidateAssessment,
    model_gateway: ModelGateway,
) -> _ExtractionOutcome:
    """Extract requirements from exactly one eligible posting candidate."""

    candidate = assessment.candidate
    try:
        response = model_gateway.generate_structured(
            role=ModelRole.EXTRACTION,
            output_schema=PostingRequirementResult,
            system_prompt=REQUIREMENT_SYSTEM_PROMPT,
            user_prompt=build_requirement_prompt(candidate),
            temperature=0,
            max_tokens=4096,
            metadata={
                "task_type": "posting_requirement_extraction",
                "prompt_version": PROMPT_VERSION,
                "posting_candidate_id": str(candidate.candidate_id),
            },
        )
        extracted = PostingRequirementResult.model_validate(response.structured_output)
    except (ModelGatewayError, TypeError, ValueError) as error:
        logger.warning(
            "posting_requirement_extraction_failed posting_candidate_id=%s",
            candidate.candidate_id,
        )
        return _ExtractionOutcome(
            requirements=[],
            limitations=[f"Requirements could not be extracted for {candidate.source_reference}."],
            raw_count=0,
            capability_count=0,
            responsibility_count=0,
            preference_count=0,
            prerequisite_count=0,
            rejected_count=0,
            unsupported_count=0,
            audit_items=[],
            failure_category=type(error).__name__,
        )

    requirements: list[RoleRequirement] = []
    unsupported = 0
    rejected = 0
    capability_count = 0
    responsibility_count = 0
    preference_count = 0
    prerequisite_count = 0
    seen: set[tuple[str, str]] = set()
    audit_items: list[PostingRequirementAuditItem] = []
    conflicting_body_role = _body_title_mismatch(candidate.title, candidate.posting_text)
    for item in extracted.requirements:
        if not _contains_quote(item.source_quote, candidate.posting_text):
            unsupported += 1
            audit_items.append(
                PostingRequirementAuditItem(
                    source_quote=item.source_quote,
                    normalized_capability=(item.normalized_capability or "")[:120] or None,
                    category=item.category,
                    item_type=item.item_type,
                    accepted=False,
                    final_classification="REJECTED_UNGROUNDED",
                    rejection_or_override_reason=(
                        "Source quote was not found in the bounded posting text."
                    ),
                )
            )
            continue
        if conflicting_body_role:
            rejected += 1
            audit_items.append(
                PostingRequirementAuditItem(
                    source_quote=item.source_quote,
                    normalized_capability=(item.normalized_capability or "")[:120] or None,
                    category=item.category,
                    item_type=item.item_type,
                    accepted=False,
                    final_classification="REJECTED_SOURCE_TITLE_MISMATCH",
                    rejection_or_override_reason=(
                        "Posting body self-identifies as "
                        f"'{conflicting_body_role}', which does not align with "
                        f"the listing title '{candidate.title}'."
                    ),
                )
            )
            continue
        group = _item_group(item)
        if group is RequirementItemType.METADATA_NON_REQUIREMENT:
            rejected += 1
            audit_items.append(
                PostingRequirementAuditItem(
                    source_quote=item.source_quote,
                    normalized_capability=(item.normalized_capability or "")[:120] or None,
                    category=item.category,
                    item_type=item.item_type,
                    accepted=False,
                    final_classification="REJECTED_NON_REQUIREMENT",
                    rejection_or_override_reason=(
                        "Deterministic policy classified the text as non-requirement metadata."
                    ),
                )
            )
            continue
        capability = canonical_capability((item.normalized_capability or item.source_quote).strip())
        if not _is_concise_capability(capability) or _is_role_label_restatement(
            capability, candidate.title
        ):
            rejected += 1
            audit_items.append(
                PostingRequirementAuditItem(
                    source_quote=item.source_quote,
                    normalized_capability=capability[:120] or None,
                    category=item.category,
                    item_type=item.item_type,
                    accepted=False,
                    final_classification="REJECTED_NON_CANONICAL",
                    rejection_or_override_reason=(
                        "Normalized capability was vague, role-restating, or not concise enough "
                        "for canonical use."
                    ),
                )
            )
            continue
        aligned, alignment_reason = quote_capability_alignment(item.source_quote, capability)
        if not aligned:
            rejected += 1
            audit_items.append(
                PostingRequirementAuditItem(
                    source_quote=item.source_quote,
                    normalized_capability=capability,
                    category=item.category,
                    item_type=item.item_type,
                    accepted=False,
                    final_classification="REJECTED_SEMANTIC_MISMATCH",
                    rejection_or_override_reason=alignment_reason,
                )
            )
            continue
        key = (group.value, item.category.value, normalize_requirement(capability))
        if not key[1] or key in seen:
            audit_items.append(
                PostingRequirementAuditItem(
                    source_quote=item.source_quote,
                    normalized_capability=capability,
                    category=item.category,
                    item_type=item.item_type,
                    accepted=False,
                    final_classification="DEDUPLICATED_WITHIN_POSTING",
                    rejection_or_override_reason=(
                        "Equivalent capability was already accepted from this posting."
                    ),
                )
            )
            continue
        seen.add(key)
        if group is RequirementItemType.PREREQUISITE:
            prerequisite_count += 1
        elif group is RequirementItemType.ROLE_RESPONSIBILITY:
            responsibility_count += 1
        elif group is RequirementItemType.PREFERENCE:
            preference_count += 1
        else:
            capability_count += 1
        comparison_eligible = group in {
            RequirementItemType.HIRING_CAPABILITY,
            RequirementItemType.PREREQUISITE,
        }
        preferred = group is RequirementItemType.PREFERENCE or (
            item.preferred if comparison_eligible else False
        )
        requirement = RoleRequirement(
            posting_id=candidate.posting_id,
            category=item.category,
            statement_type=_statement_type(group),
            requirement_text=item.source_quote.strip(),
            normalized_capability=capability,
            mandatory=item.mandatory if comparison_eligible else False,
            preferred=preferred,
            years_required=item.years_required,
            maturity_expected=item.maturity_expected,
            extraction_confidence=item.confidence,
        )
        requirements.append(requirement)
        audit_items.append(
            PostingRequirementAuditItem(
                source_requirement_id=requirement.requirement_id,
                source_quote=item.source_quote,
                normalized_capability=capability,
                category=item.category,
                item_type=group,
                accepted=True,
                final_classification="ACCEPTED_PENDING_CANONICALIZATION",
            )
        )
    limitations = list(extracted.limitations)
    if unsupported:
        limitations.append(
            f"Rejected {unsupported} requirements without exact support in the posting text."
        )
    if rejected:
        limitations.append(f"Rejected {rejected} metadata or non-canonical items.")
    return _ExtractionOutcome(
        requirements=requirements,
        limitations=limitations,
        raw_count=len(extracted.requirements),
        capability_count=capability_count,
        responsibility_count=responsibility_count,
        preference_count=preference_count,
        prerequisite_count=prerequisite_count,
        rejected_count=rejected,
        unsupported_count=unsupported,
        audit_items=audit_items,
    )


def _aggregate(
    extracted: list[tuple[PostingCandidateAssessment, list[RoleRequirement]]],
) -> list[AggregatedRequirement]:
    exact_total = sum(item.title_match is PostingTitleMatch.EXACT_TARGET for item, _ in extracted)
    variant_total = sum(
        item.title_match is PostingTitleMatch.TARGET_VARIANT for item, _ in extracted
    )
    target_total = exact_total + variant_total
    combined_total = len(extracted)
    grouped: dict[tuple[str, str], dict[str, object]] = defaultdict(
        lambda: {
            "ids": [],
            "exact": set(),
            "variant": set(),
            "related": set(),
            "display": "",
            "category": RequirementCategory.OTHER,
        }
    )
    for assessment, requirements in extracted:
        posting_id = assessment.candidate.posting_id
        for requirement in requirements:
            if requirement.statement_type in {
                RequirementStatementType.ROLE_RESPONSIBILITY,
                RequirementStatementType.PREFERENCE,
            }:
                continue
            display = requirement.normalized_capability or requirement.requirement_text
            group = (
                "prerequisite" if requirement.category in PREREQUISITE_CATEGORIES else "capability"
            )
            key = (group, normalize_requirement(display))
            bucket = grouped[key]
            bucket["display"] = display
            if bucket["category"] is RequirementCategory.OTHER:
                bucket["category"] = requirement.category
            ids = bucket["ids"]
            assert isinstance(ids, list)
            ids.append(requirement.requirement_id)
            if assessment.title_match is PostingTitleMatch.EXACT_TARGET:
                occurrence_key = "exact"
            elif assessment.title_match is PostingTitleMatch.TARGET_VARIANT:
                occurrence_key = "variant"
            else:
                occurrence_key = "related"
            occurrences = bucket[occurrence_key]
            assert isinstance(occurrences, set)
            occurrences.add(posting_id)

    output: list[AggregatedRequirement] = []
    for bucket in grouped.values():
        exact = len(bucket["exact"])
        variant = len(bucket["variant"])
        related = len(bucket["related"])
        ids = bucket["ids"]
        display = bucket["display"]
        category = bucket["category"]
        assert isinstance(ids, list)
        assert isinstance(display, str)
        assert isinstance(category, RequirementCategory)
        output.append(
            AggregatedRequirement(
                category=category,
                normalized_capability=display,
                requirement_ids=ids,
                exact_title_occurrence_count=exact,
                target_variant_occurrence_count=variant,
                related_title_occurrence_count=related,
                exact_title_frequency=exact / exact_total if exact_total else None,
                exact_and_variant_frequency=(
                    (exact + variant) / target_total if target_total else None
                ),
                combined_frequency=(
                    (exact + variant + related) / combined_total if combined_total else 0
                ),
            )
        )
    return sorted(
        output,
        key=lambda item: (-item.combined_frequency, item.normalized_capability.casefold()),
    )


def _title_tokens(value: str) -> set[str]:
    return set(normalize_requirement(value).split())


def _seniority_band(value: str) -> int:
    normalized = f" {normalize_requirement(value)} "
    if any(term in normalized for term in (" chief ", " vice president ", " vp ")):
        return 6
    if any(term in normalized for term in (" director ", " head ")):
        return 5
    if " senior manager " in normalized:
        return 4
    if any(term in normalized for term in (" senior ", " principal ", " staff ", " lead ")):
        return 3
    if any(term in normalized for term in (" associate ", " intermediate ")):
        return 2
    if any(term in normalized for term in (" junior ", " entry ", " intern ")):
        return 1
    return 2


def _observed_variant_groups(
    assessments: list[PostingCandidateAssessment], target_role: str
) -> list[tuple[str, list[PostingCandidateAssessment]]]:
    grouped: dict[str, list[PostingCandidateAssessment]] = defaultdict(list)
    display: dict[str, str] = {}
    target_tokens = _title_tokens(target_role)
    for assessment in assessments:
        if assessment.title_match is not PostingTitleMatch.RELATED_TITLE:
            continue
        title = assessment.candidate.title
        key = normalize_requirement(title)
        grouped[key].append(assessment)
        display.setdefault(key, title)

    def score(key: str) -> tuple[float, str]:
        tokens = _title_tokens(display[key])
        union = target_tokens | tokens
        similarity = len(target_tokens & tokens) / len(union) if union else 0
        return -similarity, key

    return [
        (display[key], grouped[key])
        for key in sorted(grouped, key=score)[:MAX_VARIANT_CANDIDATE_TITLES]
    ]


def _validate_target_variants(
    *,
    target_role: str,
    groups: list[tuple[str, list[PostingCandidateAssessment]]],
    requirements: list[RoleRequirement],
    exact_requirement_names: list[str],
    model_gateway: ModelGateway,
) -> list[TargetVariantAudit]:
    """Validate observed titles once, with deterministic guardrails around one model call."""

    requirements_by_posting: dict[object, list[RoleRequirement]] = defaultdict(list)
    for requirement in requirements:
        requirements_by_posting[requirement.posting_id].append(requirement)
    audits: list[TargetVariantAudit] = []
    semantic_groups = []
    target_band = _seniority_band(target_role)
    target_tokens = _title_tokens(target_role)
    for title, supporting in groups:
        posting_ids = sorted((item.candidate.posting_id for item in supporting), key=str)
        observed = [
            item
            for assessment in supporting
            for item in requirements_by_posting[assessment.candidate.posting_id]
        ]
        band_difference = abs(_seniority_band(title) - target_band)
        if band_difference >= 2:
            audits.append(
                TargetVariantAudit(
                    candidate_title=title,
                    source_posting_ids=posting_ids[:10],
                    original_classification=PostingTitleMatch.RELATED_TITLE,
                    validated_classification=PostingTitleMatch.RELATED_TITLE,
                    seniority_alignment=SeniorityAlignment.MISALIGNED,
                    confidence=ConfidenceLevel.HIGH,
                    reason="Deterministic seniority bands indicate materially different scope.",
                )
            )
            continue
        candidate_tokens = _title_tokens(title)
        if candidate_tokens == target_tokens:
            if not observed:
                audits.append(
                    TargetVariantAudit(
                        candidate_title=title,
                        source_posting_ids=posting_ids[:10],
                        original_classification=PostingTitleMatch.RELATED_TITLE,
                        validated_classification=PostingTitleMatch.RELATED_TITLE,
                        seniority_alignment=SeniorityAlignment.ALIGNED,
                        confidence=ConfidenceLevel.INSUFFICIENT,
                        reason="Equivalent title wording lacked usable requirement evidence.",
                    )
                )
                continue
            audits.append(
                TargetVariantAudit(
                    candidate_title=title,
                    source_posting_ids=posting_ids[:10],
                    original_classification=PostingTitleMatch.RELATED_TITLE,
                    validated_classification=PostingTitleMatch.TARGET_VARIANT,
                    seniority_alignment=SeniorityAlignment.ALIGNED,
                    functional_overlap=1,
                    ownership_overlap=1,
                    scope_overlap=1,
                    outcome_overlap=1,
                    core_requirement_overlap=1,
                    confidence=ConfidenceLevel.HIGH,
                    reason="Normalized title tokens are identical and seniority is aligned.",
                    promoted=True,
                )
            )
            continue
        semantic_groups.append((title, supporting, observed))

    if not semantic_groups:
        return audits
    try:
        response = model_gateway.generate_structured(
            role=ModelRole.VALIDATION,
            output_schema=TargetVariantAssessmentResult,
            system_prompt=VARIANT_SYSTEM_PROMPT,
            user_prompt=build_variant_prompt(
                target_role=target_role,
                candidates=semantic_groups,
                exact_requirements=exact_requirement_names,
            ),
            temperature=0,
            max_tokens=2400,
            metadata={
                "task_type": "target_variant_validation",
                "prompt_version": VARIANT_PROMPT_VERSION,
            },
        )
        result = TargetVariantAssessmentResult.model_validate(response.structured_output)
    except (ModelGatewayError, TypeError, ValueError):
        return audits + [
            TargetVariantAudit(
                candidate_title=title,
                source_posting_ids=[item.candidate.posting_id for item in supporting][:10],
                original_classification=PostingTitleMatch.RELATED_TITLE,
                validated_classification=PostingTitleMatch.RELATED_TITLE,
                seniority_alignment=SeniorityAlignment.UNCERTAIN,
                confidence=ConfidenceLevel.INSUFFICIENT,
                reason="Bounded semantic variant validation was unavailable.",
            )
            for title, supporting, _ in semantic_groups
        ]

    proposed = {normalize_requirement(item.candidate_title): item for item in result.assessments}
    for title, supporting, observed in semantic_groups:
        item = proposed.get(normalize_requirement(title))
        allowed_ids = {value.candidate.posting_id for value in supporting}
        has_grounded_evidence = bool(observed)
        valid_references = bool(
            item
            and item.supporting_posting_ids
            and set(item.supporting_posting_ids).issubset(allowed_ids)
        )
        promoted = bool(
            item
            and item.classification is TargetVariantClassification.VALID_TARGET_VARIANT
            and item.seniority_alignment is SeniorityAlignment.ALIGNED
            and min(
                item.functional_overlap,
                item.ownership_overlap,
                item.scope_overlap,
                item.outcome_overlap,
            )
            >= VARIANT_OVERLAP_MINIMUM
            and item.evidence_confidence in {ConfidenceLevel.HIGH, ConfidenceLevel.MODERATE}
            and has_grounded_evidence
            and valid_references
        )
        audits.append(
            TargetVariantAudit(
                candidate_title=title,
                source_posting_ids=sorted(allowed_ids, key=str)[:10],
                original_classification=PostingTitleMatch.RELATED_TITLE,
                validated_classification=(
                    PostingTitleMatch.TARGET_VARIANT
                    if promoted
                    else PostingTitleMatch.RELATED_TITLE
                ),
                seniority_alignment=(
                    item.seniority_alignment if item else SeniorityAlignment.UNCERTAIN
                ),
                functional_overlap=item.functional_overlap if item else None,
                ownership_overlap=item.ownership_overlap if item else None,
                scope_overlap=item.scope_overlap if item else None,
                outcome_overlap=item.outcome_overlap if item else None,
                core_requirement_overlap=(item.core_requirement_overlap if item else None),
                confidence=(item.evidence_confidence if item else ConfidenceLevel.INSUFFICIENT),
                reason=(
                    item.reasoning_summary
                    if item and has_grounded_evidence and valid_references
                    else "Variant evidence or posting provenance was insufficient."
                ),
                promoted=promoted,
            )
        )
    return audits


def analyze_market_requirements(
    sources: list[RetainedSourceContent] | list[MarketPostingEvidence],
    *,
    target_role: str,
    geography: str,
    model_gateway: ModelGateway,
    allow_related_titles: bool = True,
    enable_target_variant_expansion: bool = False,
    posting_limit: int | None = None,
    now: datetime | None = None,
) -> MarketRequirementAnalysis:
    """Run the amended 5B flow without candidate-profile data or career reasoning."""

    if posting_limit is not None and posting_limit < 1:
        raise ValueError("posting_limit must be greater than zero")

    timestamp = now or datetime.now(UTC)
    structured = bool(sources) and isinstance(sources[0], MarketPostingEvidence)
    posting_by_id: dict = {}
    enrichment_by_posting: dict = {}
    if structured:
        evidence_items = [item for item in sources if isinstance(item, MarketPostingEvidence)]
        source_results = []
        assessments = [
            assessment
            for item in evidence_items
            if (assessment := _assessment_from_evidence(item, target_role=target_role)) is not None
        ]
        posting_by_id = {item.posting.posting_id: item.posting for item in evidence_items}
        enrichment_by_posting = {
            item.posting.posting_id: item.enrichment_status is EnrichmentStatus.APPLIED
            for item in evidence_items
        }
        limitations = [note for item in evidence_items for note in item.limitations]
        empty_evidence_count = len(evidence_items) - len(assessments)
        if empty_evidence_count:
            limitations.append(
                f"{empty_evidence_count} structured postings had no usable description evidence."
            )
    else:
        retained_sources = [item for item in sources if isinstance(item, RetainedSourceContent)]
        source_results = [
            classify_and_segment_source(item, model_gateway=model_gateway)
            for item in retained_sources
        ]
        assessments = [
            assess_candidate(candidate, target_role=target_role, target_geography=geography)
            for result in source_results
            for candidate in result.candidates
        ]
        limitations = [note for result in source_results for note in result.limitations]
    assessments = _deduplicate_assessments(assessments)
    all_eligible = [
        item
        for item in assessments
        if item.geography_status is PostingGeographyStatus.IN_SCOPE
        and item.title_match is not PostingTitleMatch.IRRELEVANT
        and (
            allow_related_titles
            or item.title_match
            in {PostingTitleMatch.EXACT_TARGET, PostingTitleMatch.TARGET_VARIANT}
        )
    ]
    if structured:
        all_eligible.sort(key=_scope_order)
    eligible = list(all_eligible)
    if posting_limit is not None:
        eligible = _select_employer_diverse(eligible, posting_limit)

    extracted: list[tuple[PostingCandidateAssessment, list[RoleRequirement]]] = []
    posting_quality: list[PostingExtractionQuality] = []
    posting_audits: list[PostingRequirementAudit] = []
    failed_extraction_count = 0
    for assessment in eligible:
        outcome = extract_posting_requirements(assessment, model_gateway)
        limitations.extend(outcome.limitations)
        quality, audit = _quality_and_audit(
            assessment,
            outcome,
            enrichment_used=enrichment_by_posting.get(assessment.candidate.posting_id, False),
        )
        posting_quality.append(quality)
        posting_audits.append(audit)
        if outcome.failure_category:
            failed_extraction_count += 1
            continue
        extracted.append((assessment, outcome.requirements))

    initial_raw_requirements = [item for _, items in extracted for item in items]
    initial_exact = sum(item.title_match is PostingTitleMatch.EXACT_TARGET for item, _ in extracted)
    initial_variant = sum(
        item.title_match is PostingTitleMatch.TARGET_VARIANT for item, _ in extracted
    )
    initial_related = sum(
        item.title_match is PostingTitleMatch.RELATED_TITLE for item, _ in extracted
    )
    initial_summary = MarketRequirementSummary(
        target_role=target_role,
        geography=geography,
        source_page_count=len(sources),
        identified_candidate_count=len(assessments),
        validated_in_scope_posting_count=len(eligible),
        analyzed_posting_count=len(extracted),
        exact_title_analyzed_count=initial_exact,
        target_variant_analyzed_count=initial_variant,
        related_title_analyzed_count=initial_related,
        out_of_scope_count=sum(
            item.geography_status is PostingGeographyStatus.OUT_OF_SCOPE for item in assessments
        ),
        unclear_geography_count=sum(
            item.geography_status is PostingGeographyStatus.UNCLEAR for item in assessments
        ),
        irrelevant_title_count=sum(
            item.title_match is PostingTitleMatch.IRRELEVANT for item in assessments
        ),
    )
    initial_profile, posting_audits = build_canonical_target_role_profile(
        target_role=target_role,
        geography=geography,
        requirements=initial_raw_requirements,
        assessments=assessments,
        summary=initial_summary,
        posting_audits=posting_audits,
        generated_at=timestamp,
    )
    variant_audits: list[TargetVariantAudit] = []
    expansion_attempted = bool(
        enable_target_variant_expansion
        and allow_related_titles
        and initial_profile.profile_status is RoleProfileStatus.INSUFFICIENT
    )
    if expansion_attempted:
        groups = _observed_variant_groups(all_eligible, target_role)
        already_extracted = {item.candidate.posting_id for item, _ in extracted}
        extra_candidates = [
            assessment
            for _, supporting in groups
            for assessment in supporting
            if assessment.candidate.posting_id not in already_extracted
        ][:MAX_VARIANT_POSTINGS]
        for assessment in extra_candidates:
            outcome = extract_posting_requirements(assessment, model_gateway)
            limitations.extend(outcome.limitations)
            quality, audit = _quality_and_audit(
                assessment,
                outcome,
                enrichment_used=enrichment_by_posting.get(assessment.candidate.posting_id, False),
            )
            posting_quality.append(quality)
            posting_audits.append(audit)
            eligible.append(assessment)
            if outcome.failure_category:
                failed_extraction_count += 1
            else:
                extracted.append((assessment, outcome.requirements))

        expanded_raw = [item for _, items in extracted for item in items]
        exact_names = [
            item.display_name
            for item in [
                *initial_profile.requirements,
                *initial_profile.prerequisites,
                *initial_profile.optional_signals,
            ]
        ]
        variant_audits = _validate_target_variants(
            target_role=target_role,
            groups=groups,
            requirements=expanded_raw,
            exact_requirement_names=exact_names,
            model_gateway=model_gateway,
        )
        promoted_ids = {
            posting_id
            for audit in variant_audits
            if audit.promoted
            for posting_id in audit.source_posting_ids
        }

        def promoted(assessment: PostingCandidateAssessment) -> PostingCandidateAssessment:
            if assessment.candidate.posting_id not in promoted_ids:
                return assessment
            return assessment.model_copy(update={"title_match": PostingTitleMatch.TARGET_VARIANT})

        assessments = [promoted(item) for item in assessments]
        all_eligible = [promoted(item) for item in all_eligible]
        eligible = list({item.candidate.posting_id: promoted(item) for item in eligible}.values())
        extracted = [(promoted(item), values) for item, values in extracted]
        posting_audits = [
            audit.model_copy(
                update={
                    "title_classification": (
                        PostingTitleMatch.TARGET_VARIANT
                        if audit.posting_id in promoted_ids
                        else audit.title_classification
                    )
                }
            )
            for audit in posting_audits
        ]

    requirements = [requirement for _, items in extracted for requirement in items]
    frequencies = _aggregate(extracted)
    capability_frequencies = [
        item for item in frequencies if item.category not in PREREQUISITE_CATEGORIES
    ]
    prerequisite_frequencies = [
        item for item in frequencies if item.category in PREREQUISITE_CATEGORIES
    ]
    frequency_by_id = {
        requirement_id: aggregate.combined_frequency
        for aggregate in frequencies
        for requirement_id in aggregate.requirement_ids
    }
    requirements = [
        item.model_copy(
            update={"frequency_within_sample": frequency_by_id.get(item.requirement_id)}
        )
        for item in requirements
    ]
    analyzed_ids = {item.candidate.posting_id for item, _ in extracted}
    postings = [
        posting_by_id.get(item.candidate.posting_id)
        or _posting(item.candidate, retrieved_at=timestamp)
        for item in eligible
        if item.candidate.posting_id in analyzed_ids
    ]
    exact_count = sum(item.title_match is PostingTitleMatch.EXACT_TARGET for item, _ in extracted)
    variant_count = sum(
        item.title_match is PostingTitleMatch.TARGET_VARIANT for item, _ in extracted
    )
    related_count = sum(
        item.title_match is PostingTitleMatch.RELATED_TITLE for item, _ in extracted
    )
    summary = MarketRequirementSummary(
        target_role=target_role,
        geography=geography,
        source_page_count=len(sources),
        identified_candidate_count=len(assessments),
        validated_in_scope_posting_count=len(eligible),
        analyzed_posting_count=len(extracted),
        exact_title_analyzed_count=exact_count,
        target_variant_analyzed_count=variant_count,
        related_title_analyzed_count=related_count,
        out_of_scope_count=sum(
            item.geography_status is PostingGeographyStatus.OUT_OF_SCOPE for item in assessments
        ),
        unclear_geography_count=sum(
            item.geography_status is PostingGeographyStatus.UNCLEAR for item in assessments
        ),
        irrelevant_title_count=sum(
            item.title_match is PostingTitleMatch.IRRELEVANT for item in assessments
        ),
        requirements=frequencies,
        capability_requirements=capability_frequencies,
        prerequisite_requirements=prerequisite_frequencies,
        posting_quality=posting_quality,
        limitations=list(dict.fromkeys(limitations)),
    )
    if not eligible:
        status = RequirementRunStatus.EMPTY
    elif not extracted:
        status = RequirementRunStatus.FAILED
    elif failed_extraction_count:
        status = RequirementRunStatus.PARTIAL
    else:
        status = RequirementRunStatus.SUCCEEDED
    canonical_profile, posting_audits = build_canonical_target_role_profile(
        target_role=target_role,
        geography=geography,
        requirements=requirements,
        assessments=assessments,
        summary=summary,
        posting_audits=posting_audits,
        generated_at=timestamp,
    )
    canonical_requirements = [
        item.as_role_requirement() for item in canonical_profile.comparison_requirements
    ]
    return MarketRequirementAnalysis(
        status=status,
        source_results=source_results,
        assessments=assessments,
        postings=postings,
        requirements=canonical_requirements,
        raw_requirements=requirements,
        canonical_profile=canonical_profile,
        initial_canonical_profile=initial_profile,
        posting_audits=posting_audits,
        target_variant_audits=variant_audits,
        target_variant_expansion_attempted=expansion_attempted,
        summary=summary,
    )
