"""Classify untrusted source content and segment posting-specific units."""

import re

from ai_career_navigator.domain import ConfidenceLevel, GeographyScope
from ai_career_navigator.market.normalization import normalize_whitespace, normalized_comparison
from ai_career_navigator.market.requirement_prompts import (
    PROMPT_VERSION,
    SEGMENTATION_SYSTEM_PROMPT,
    build_segmentation_prompt,
)
from ai_career_navigator.market.requirement_schemas import (
    ModelSegmentationResult,
    PostingCandidate,
    PostingCandidateAssessment,
    PostingGeographyStatus,
    PostingTitleMatch,
    SourceContentType,
    SourceProcessingResult,
)
from ai_career_navigator.market.schemas import PostingSeniority, RetainedSourceContent
from ai_career_navigator.market.validation import (
    HIRING_SIGNALS,
    is_aggregator_title,
    is_clean_posting_title,
    is_target_title_variant,
    is_url_like_title,
    title_is_grounded,
    title_is_relevant,
)
from ai_career_navigator.models import ModelGateway, ModelGatewayError, ModelRole

ROLE_WORDS = re.compile(
    r"\b(architect|engineer|developer|manager|director|lead|analyst|consultant|specialist)\b",
    re.IGNORECASE,
)
NON_POSTING_HEADINGS = re.compile(
    r"\b(salary|salaries|faq|frequently asked|career advice|job alert|related jobs)\b",
    re.IGNORECASE,
)
POSTING_SECTION_HEADING = re.compile(
    r"^(?:what|who|how|why|about|our|your|meet)\b|"
    r"\b(?:responsibilities|qualifications|requirements|duties|skills)\s*:?$",
    re.IGNORECASE,
)
PAGE_FOOTER_HEADING = re.compile(
    r"\b(?:related jobs|similar jobs|recommended jobs|other opportunities|career advice|"
    r"job alerts?|privacy policy|cookie policy|terms of (?:use|service))\b",
    re.IGNORECASE,
)
AGGREGATOR_CLAIM = re.compile(r"\b([\d,]+)(?:\+)?\s+(?:open\s+)?jobs?\b", re.IGNORECASE)
HEADING = re.compile(r"^\s{0,3}#{1,4}\s+(.+?)\s*$")
STRONG_HEADING = re.compile(r"^\s*\*\*(.+?)\*\*\s*$")
FIELD = re.compile(r"^(employer|company|location)\s*:\s*(.+)$", re.IGNORECASE)
LOCATION_FIELD = re.compile(r"^(?:job\s+|work\s+|workplace\s+)?location\s*:\s*(.+)$", re.IGNORECASE)
TITLE_SEPARATOR = re.compile(r"\s+(?:—|–|\|)\s+|\s+at\s+", re.IGNORECASE)
CANADA_TOKENS = {
    "canada",
    "ontario",
    "toronto",
    "vancouver",
    "british columbia",
    "alberta",
    "calgary",
    "quebec",
    "montreal",
    "ottawa",
    "burnaby",
    "edmonton",
    "halifax",
    "mississauga",
    "markham",
    "winnipeg",
    "manitoba",
    "new brunswick",
    "newfoundland and labrador",
    "nova scotia",
    "northwest territories",
    "nunavut",
    "prince edward island",
    "saskatchewan",
    "yukon",
}
US_TOKENS = {
    "united states",
    "usa",
    "u.s.",
    "san diego",
    "new york",
    "chicago",
    "seattle",
    "california",
    "texas",
    "florida",
}
TORONTO_TOKENS = {"toronto", "greater toronto area", "gta"}
OTHER_CANADA_LOCATION_TOKENS = {
    "vancouver",
    "british columbia",
    "alberta",
    "calgary",
    "quebec",
    "montreal",
    "ottawa",
}
GTA_LOCALITY_TOKENS = {
    "greater toronto area",
    "gta",
    "mississauga",
    "markham",
    "brampton",
    "vaughan",
    "richmond hill",
}
CANADIAN_PROVINCE_CODE = re.compile(r"(?:,\s*|\b)(?:AB|BC|MB|NB|NL|NS|NT|NU|ON|PE|QC|SK|YT)\b")
JUNIOR_TITLE = re.compile(r"\b(?:associate|junior|jr\.?)\b", re.IGNORECASE)
SENIOR_TITLE = re.compile(r"\b(?:senior|sr\.?)\b", re.IGNORECASE)
STAFF_TITLE = re.compile(r"\b(?:staff|principal|lead|head|director)\b", re.IGNORECASE)


def _is_explicit_canadian_location(location: str) -> bool:
    observed = normalize_whitespace(location).casefold()
    return bool(
        any(token in observed for token in CANADA_TOKENS) or CANADIAN_PROVINCE_CODE.search(location)
    )


def _headings(markdown: str) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for index, line in enumerate(markdown.splitlines()):
        match = HEADING.match(line) or STRONG_HEADING.match(line)
        if match:
            found.append((index, normalize_whitespace(match.group(1))))
    return found


def _is_posting_heading(heading: str) -> bool:
    return bool(
        ROLE_WORDS.search(heading)
        and not NON_POSTING_HEADINGS.search(heading)
        and not POSTING_SECTION_HEADING.search(heading)
        and not PAGE_FOOTER_HEADING.search(heading)
    )


def _heading_depth(line: str) -> int:
    match = re.match(r"^\s{0,3}(#{1,4})\s", line)
    # Bold-only headings have no hierarchy: the next bold/Markdown section is a peer.
    return len(match.group(1)) if match else 1


def _posting_section_lines(lines: list[str]) -> list[str]:
    """Keep vacancy subsections, excluding page-footer and non-posting sections."""
    headings = _headings("\n".join(lines))
    omitted: set[int] = set()
    for position, (start, heading) in enumerate(headings):
        if PAGE_FOOTER_HEADING.search(heading):
            return [line for index, line in enumerate(lines[:start]) if index not in omitted]
        if not NON_POSTING_HEADINGS.search(heading):
            continue
        depth = _heading_depth(lines[start])
        end = next(
            (
                next_start
                for next_start, next_heading in headings[position + 1 :]
                if _heading_depth(lines[next_start]) <= depth or _is_posting_heading(next_heading)
            ),
            len(lines),
        )
        omitted.update(range(start, end))
    return [line for index, line in enumerate(lines) if index not in omitted]


def _split_posting_heading(heading: str) -> tuple[str, str | None, str | None]:
    parts = [normalize_whitespace(part) for part in TITLE_SEPARATOR.split(heading) if part]
    title = parts[0] if parts else normalize_whitespace(heading)
    employer = parts[1] if len(parts) > 1 else None
    location = parts[2] if len(parts) > 2 else None
    return title, employer, location


def _field_value(lines: list[str], field_name: str) -> str | None:
    for line in lines[:8]:
        cleaned = line.strip().strip("*- ")
        match = FIELD.match(cleaned)
        if match and match.group(1).casefold() in field_name:
            return normalize_whitespace(match.group(2))
    return None


def _location_grounding(text: str) -> tuple[str | None, str | None]:
    """Return only location text explicitly present in one posting segment."""

    lines = [normalize_whitespace(line.strip().strip("#*- ")) for line in text.splitlines()]
    lines = [line for line in lines if line]
    for line in lines:
        match = LOCATION_FIELD.match(line)
        if match:
            value = normalize_whitespace(match.group(1))[:500]
            return value, line[:500]

    scored: list[tuple[int, int, str]] = []
    for index, line in enumerate(lines):
        folded = line.casefold()
        score = 0
        if "remote" in folded and "canada" in folded:
            score = 50
        elif any(token in folded for token in TORONTO_TOKENS):
            score = 40
        elif "ontario" in folded:
            score = 30
        elif any(token in folded for token in US_TOKENS):
            score = 25
        elif _is_explicit_canadian_location(line):
            score = 10
        if score:
            scored.append((score, -index, line[:500]))
    if not scored:
        return None, None
    evidence = max(scored)[2]
    return evidence, evidence


def _looks_like_posting(title: str, text: str) -> bool:
    folded = text.casefold()
    return bool(ROLE_WORDS.search(title)) and any(signal in folded for signal in HIRING_SIGNALS)


def _deterministic_candidates(
    item: RetainedSourceContent,
) -> tuple[list[PostingCandidate], int, int, int]:
    markdown = item.content.markdown
    lines = markdown.splitlines()
    headings = _headings(markdown)
    footer_start = next(
        (start for start, heading in headings if PAGE_FOOTER_HEADING.search(heading)),
        len(lines),
    )
    posting_headings = [
        (start, heading)
        for start, heading in headings
        if start < footer_start and _is_posting_heading(heading)
    ]
    candidates: list[PostingCandidate] = []
    segmented_count = 0
    rejected_url_like = 0
    rejected_search_heading = 0
    for position, (start, heading) in enumerate(posting_headings):
        end = (
            posting_headings[position + 1][0]
            if position + 1 < len(posting_headings)
            else footer_start
        )
        section_lines = _posting_section_lines(lines[start:end])
        section = "\n".join(section_lines).strip()
        if not _looks_like_posting(heading, section):
            continue
        segmented_count += 1
        title, heading_employer, heading_location = _split_posting_heading(heading)
        if is_url_like_title(title):
            rejected_url_like += 1
            continue
        if is_aggregator_title(title):
            rejected_search_heading += 1
            continue
        if not is_clean_posting_title(title) or not title_is_grounded(title, section):
            continue
        employer = _field_value(section_lines[1:], "employercompany") or heading_employer
        location = _field_value(section_lines[1:], "location") or heading_location
        grounded_location, location_evidence = _location_grounding(section)
        location = location or grounded_location
        if location and location_evidence is None:
            location_evidence = location
        excerpt = normalize_whitespace(" ".join(section_lines[:4]))[:2000]
        candidates.append(
            PostingCandidate(
                source_id=item.source.source_id,
                source_reference=" > ".join(
                    part for part in (item.source.title, employer, title) if part
                ),
                source_reference_text=excerpt,
                title=title,
                employer=employer,
                location=location,
                location_evidence_text=location_evidence,
                posting_text=section[:20_000],
                extraction_confidence=ConfidenceLevel.HIGH,
            )
        )
    return candidates, segmented_count, rejected_url_like, rejected_search_heading


def _direct_candidate(item: RetainedSourceContent) -> PostingCandidate | None:
    source_page_title = item.content.title or item.source.title
    text = "\n".join(_posting_section_lines(item.content.markdown.splitlines())).strip()
    if not text or not _looks_like_posting(source_page_title, text):
        return None
    title, title_employer, title_location = _split_posting_heading(source_page_title)
    if not is_clean_posting_title(title):
        return None
    if item.content.title is None and not title_is_grounded(title, text):
        return None
    employer = item.content.employer or title_employer or item.source.employer
    grounded_location, location_evidence = _location_grounding(text)
    location = item.content.location or title_location or grounded_location
    if item.content.location:
        location_evidence = item.content.location
    elif title_location:
        location_evidence = source_page_title
    return PostingCandidate(
        source_id=item.source.source_id,
        source_reference=" > ".join(part for part in (item.source.title, employer, title) if part),
        source_reference_text=normalize_whitespace(text)[:2000],
        title=title,
        employer=employer,
        location=location,
        location_evidence_text=location_evidence,
        posting_text=text[:20_000],
        extraction_confidence=(
            ConfidenceLevel.HIGH if item.content.title else ConfidenceLevel.MODERATE
        ),
    )


def _is_grounded(value: str, source: str) -> bool:
    return normalize_whitespace(value).casefold() in normalize_whitespace(source).casefold()


def _model_candidates(
    item: RetainedSourceContent, gateway: ModelGateway
) -> tuple[list[PostingCandidate], list[str], int, int, int]:
    try:
        response = gateway.generate_structured(
            role=ModelRole.EXTRACTION,
            output_schema=ModelSegmentationResult,
            system_prompt=SEGMENTATION_SYSTEM_PROMPT,
            user_prompt=build_segmentation_prompt(
                title=item.source.title,
                content=item.content.markdown[:50_000],
            ),
            temperature=0,
            max_tokens=4096,
            metadata={"task_type": "posting_segmentation", "prompt_version": PROMPT_VERSION},
        )
        result = ModelSegmentationResult.model_validate(response.structured_output)
    except (ModelGatewayError, TypeError, ValueError):
        return [], ["Irregular source content could not be segmented safely."], 0, 0, 0

    candidates: list[PostingCandidate] = []
    rejected = 0
    rejected_url_like = 0
    rejected_search_heading = 0
    for proposed in result.candidates:
        if not _is_grounded(proposed.source_reference_text, item.content.markdown):
            rejected += 1
            continue
        if not _is_grounded(proposed.posting_text, item.content.markdown):
            rejected += 1
            continue
        if is_url_like_title(proposed.title):
            rejected_url_like += 1
            continue
        if is_aggregator_title(proposed.title):
            rejected_search_heading += 1
            continue
        if not is_clean_posting_title(proposed.title) or not title_is_grounded(
            proposed.title, proposed.posting_text
        ):
            rejected += 1
            continue
        if proposed.employer and not _is_grounded(proposed.employer, proposed.posting_text):
            rejected += 1
            continue
        if proposed.location and not _is_grounded(proposed.location, proposed.posting_text):
            rejected += 1
            continue
        candidates.append(
            PostingCandidate(
                source_id=item.source.source_id,
                source_reference=" > ".join(
                    part for part in (item.source.title, proposed.employer, proposed.title) if part
                ),
                source_reference_text=proposed.source_reference_text,
                title=proposed.title,
                employer=proposed.employer,
                location=proposed.location,
                location_evidence_text=proposed.location,
                posting_text=proposed.posting_text,
                extraction_confidence=ConfidenceLevel.MODERATE,
            )
        )
    limitations = list(result.limitations)
    if rejected:
        limitations.append(
            f"Rejected {rejected} model-segmented candidates without exact source grounding."
        )
    return (
        candidates,
        limitations,
        len(result.candidates),
        rejected_url_like,
        rejected_search_heading,
    )


def classify_and_segment_source(
    item: RetainedSourceContent,
    *,
    model_gateway: ModelGateway | None = None,
) -> SourceProcessingResult:
    """Segment obvious structures deterministically, with an optional grounded fallback."""

    posting_scope_text = "\n".join(_posting_section_lines(item.content.markdown.splitlines()))
    claim_match = AGGREGATOR_CLAIM.search(
        " ".join((item.source.title, item.content.title or "", posting_scope_text[:5000]))
    )
    reported_text = claim_match.group(1).replace(",", "") if claim_match else ""
    reported_count = int(reported_text) if reported_text.isdigit() else None
    candidates, segmented_count, rejected_url_like, rejected_search_heading = (
        _deterministic_candidates(item)
    )
    limitations: list[str] = []
    has_non_posting_sections = bool(NON_POSTING_HEADINGS.search(item.content.markdown))

    if len(candidates) >= 2:
        content_type = (
            SourceContentType.MIXED_JOB_CONTENT
            if has_non_posting_sections
            else SourceContentType.AGGREGATOR_JOB_PAGE
        )
    elif reported_count is not None:
        content_type = (
            SourceContentType.MIXED_JOB_CONTENT
            if has_non_posting_sections
            else SourceContentType.AGGREGATOR_JOB_PAGE
        )
        if not candidates and model_gateway is not None:
            (
                candidates,
                limitations,
                model_segmented_count,
                model_rejected_url_like,
                model_rejected_search_heading,
            ) = _model_candidates(item, model_gateway)
            segmented_count += model_segmented_count
            rejected_url_like += model_rejected_url_like
            rejected_search_heading += model_rejected_search_heading
    else:
        if not candidates:
            source_page_title = item.content.title or item.source.title
            if _looks_like_posting(source_page_title, item.content.markdown):
                segmented_count += 1
                rejected_url_like += int(is_url_like_title(source_page_title))
                rejected_search_heading += int(is_aggregator_title(source_page_title))
            direct = _direct_candidate(item)
            candidates = [direct] if direct else []
        content_type = (
            SourceContentType.DIRECT_JOB_PAGE
            if candidates
            else SourceContentType.INSUFFICIENT_JOB_CONTENT
        )

    if len(candidates) == 1 and content_type is SourceContentType.DIRECT_JOB_PAGE:
        candidate = candidates[0]
        metadata_title, _, _ = _split_posting_heading(item.content.title or item.source.title)
        if normalized_comparison(candidate.title) == normalized_comparison(metadata_title):
            # A heading-based vacancy still belongs to this page's structured metadata.
            # Never copy page-level fields into individual cards from a jobs listing.
            candidates = [
                candidate.model_copy(
                    update={
                        "employer": candidate.employer or item.content.employer,
                        "location": candidate.location or item.content.location,
                        "location_evidence_text": candidate.location_evidence_text
                        or item.content.location,
                    }
                )
            ]

    if reported_count is not None:
        limitations.append(
            f"The source reported {reported_count} jobs; this page-level claim was not counted."
        )
    if not candidates:
        limitations.append("No independently grounded posting candidate was identified.")
    return SourceProcessingResult(
        source_id=item.source.source_id,
        content_type=content_type,
        candidates=candidates,
        segmented_candidate_count=segmented_count,
        title_grounded_candidate_count=len(candidates),
        rejected_url_like_title_count=rejected_url_like,
        rejected_search_heading_title_count=rejected_search_heading,
        aggregator_reported_count=reported_count,
        limitations=list(dict.fromkeys(limitations)),
    )


def assess_title(
    title: str, target_role: str, posting_text: str | None = None
) -> PostingTitleMatch:
    from ai_career_navigator.market.validation import is_exact_title

    if is_exact_title(title, target_role):
        return PostingTitleMatch.EXACT_TARGET
    if is_target_title_variant(title, target_role, posting_text=posting_text):
        return PostingTitleMatch.TARGET_VARIANT
    if title_is_relevant(title, target_role):
        return PostingTitleMatch.RELATED_TITLE
    generic = {
        "architect",
        "engineer",
        "developer",
        "manager",
        "director",
        "lead",
        "analyst",
        "consultant",
        "specialist",
        "senior",
        "junior",
        "solution",
        "solutions",
    }
    observed_tokens = set(normalized_comparison(title).split())
    target_tokens = set(normalized_comparison(target_role).split())
    shared_subjects = (observed_tokens & target_tokens) - generic
    if shared_subjects and ROLE_WORDS.search(title) and ROLE_WORDS.search(target_role):
        return PostingTitleMatch.RELATED_TITLE
    return PostingTitleMatch.IRRELEVANT


def classify_seniority(title: str) -> PostingSeniority:
    if STAFF_TITLE.search(title):
        return PostingSeniority.STAFF_LEAD
    if SENIOR_TITLE.search(title):
        return PostingSeniority.SENIOR
    if JUNIOR_TITLE.search(title):
        return PostingSeniority.ASSOCIATE_JUNIOR
    if ROLE_WORDS.search(title):
        return PostingSeniority.STANDARD
    return PostingSeniority.UNKNOWN


def classify_title_for_seniority(
    title: str,
    target_role: str,
    target_seniority: str | None,
    posting_text: str | None = None,
) -> PostingTitleMatch:
    """Keep materially junior/senior variants secondary when no level was requested."""

    classification = assess_title(title, target_role, posting_text=posting_text)
    if classification is PostingTitleMatch.IRRELEVANT:
        return classification
    explicit_target_level = target_seniority or (
        target_role if classify_seniority(target_role) is not PostingSeniority.STANDARD else None
    )
    if explicit_target_level:
        target_level = classify_seniority(explicit_target_level)
        observed_level = classify_seniority(title)
        if target_level is not PostingSeniority.UNKNOWN and observed_level is not target_level:
            return PostingTitleMatch.RELATED_TITLE
        return classification
    if classify_seniority(title) in {
        PostingSeniority.ASSOCIATE_JUNIOR,
        PostingSeniority.SENIOR,
        PostingSeniority.STAFF_LEAD,
    }:
        return PostingTitleMatch.RELATED_TITLE
    return classification


def assess_geography(location: str | None, target_geography: str) -> PostingGeographyStatus:
    """Apply conservative country-aware V1 geography checks."""

    if not location:
        return PostingGeographyStatus.UNCLEAR
    observed = normalize_whitespace(location).casefold()
    target = normalize_whitespace(target_geography).casefold()
    if "remote" in observed and not any(token in observed for token in CANADA_TOKENS | US_TOKENS):
        return PostingGeographyStatus.UNCLEAR
    target_is_canada = any(token in target for token in CANADA_TOKENS)
    if target_is_canada:
        if any(token in observed for token in US_TOKENS):
            return PostingGeographyStatus.OUT_OF_SCOPE
        if re.search(r"\b[A-Z][a-z .'-]+,\s*(CA|NY|WA|TX|FL)\b", location):
            return PostingGeographyStatus.OUT_OF_SCOPE
        target_is_toronto = any(token in target for token in TORONTO_TOKENS)
        if target_is_toronto:
            if any(token in observed for token in TORONTO_TOKENS) or "ontario" in observed:
                return PostingGeographyStatus.IN_SCOPE
            if "remote" in observed and "canada" in observed:
                return PostingGeographyStatus.IN_SCOPE
            if any(token in observed for token in OTHER_CANADA_LOCATION_TOKENS):
                return PostingGeographyStatus.OUT_OF_SCOPE
            return PostingGeographyStatus.UNCLEAR
        if _is_explicit_canadian_location(location):
            return PostingGeographyStatus.IN_SCOPE
        return PostingGeographyStatus.UNCLEAR
    if target in observed or observed in target:
        return PostingGeographyStatus.IN_SCOPE
    return PostingGeographyStatus.UNCLEAR


def match_geography_scope(
    location: str | None,
    requested_scope: GeographyScope | None = None,
) -> GeographyScope | None:
    """Classify only explicit posting-level location evidence into a V1 scope."""

    if not location:
        return None
    observed = normalize_whitespace(location).casefold()
    if any(token in observed for token in US_TOKENS):
        return None
    if "remote" in observed and "canada" in observed:
        return GeographyScope.COUNTRY_REMOTE
    if requested_scope is GeographyScope.COUNTRY:
        return GeographyScope.COUNTRY if _is_explicit_canadian_location(location) else None
    if any(token in observed for token in GTA_LOCALITY_TOKENS):
        return GeographyScope.METRO_AREA
    if "toronto" in observed:
        return GeographyScope.STRICT_CITY
    if "ontario" in observed or re.search(r"\bON\b", location):
        return GeographyScope.PROVINCE
    return None


def assess_candidate(
    candidate: PostingCandidate,
    *,
    target_role: str,
    target_geography: str,
    requested_geography_scope: GeographyScope | None = None,
    target_seniority: str | None = None,
) -> PostingCandidateAssessment:
    return PostingCandidateAssessment(
        candidate=candidate,
        geography_status=assess_geography(candidate.location, target_geography),
        geography_evidence_text=candidate.location_evidence_text,
        requested_geography_scope=requested_geography_scope,
        matched_geography_scope=match_geography_scope(
            candidate.location,
            requested_scope=requested_geography_scope,
        ),
        title_match=classify_title_for_seniority(
            candidate.title,
            target_role,
            target_seniority,
            posting_text=candidate.posting_text,
        ),
    )
