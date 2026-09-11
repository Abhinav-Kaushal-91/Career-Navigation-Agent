"""Explainable deterministic validation for candidate job pages."""

import re

from ai_career_navigator.market.normalization import normalized_comparison
from ai_career_navigator.market.schemas import MarketPageContent, MarketSearchResult
from ai_career_navigator.market.source_registry import looks_like_individual_job_url

REJECT_PATTERNS = (
    "salary guide",
    "salary report",
    "resume example",
    "resume template",
    "training course",
    "online course",
    "certification course",
    "/blog/",
    "/news/",
    "/articles/",
)
HIRING_SIGNALS = (
    "apply now",
    "job description",
    "responsibilities",
    "qualifications",
    "requirements",
    "we are hiring",
    "join our team",
    "employment type",
)
ROLE_WORDS = {
    "architect",
    "engineer",
    "developer",
    "manager",
    "director",
    "lead",
    "analyst",
    "consultant",
    "specialist",
}
URL_PREFIX = re.compile(r"^https?://", re.IGNORECASE)
DOMAIN_PATH = re.compile(
    r"^(?:www\.)?[a-z0-9.-]+\.[a-z]{2,}(?:/|$)|^/?(?:jobs?|careers?)/",
    re.IGNORECASE,
)
AGGREGATOR_TITLE = re.compile(
    r"^(?:[\d,]+\+?\s+)?(?:open\s+)?jobs?\b|"
    r"\bjobs?\s+in\s+.+(?:now hiring|search results)?\b|"
    r"\bjob search results\b|\bnow hiring\b",
    re.IGNORECASE,
)


def is_url_like_title(title: str) -> bool:
    """Reject URLs and strings dominated by domain/path syntax as posting titles."""

    value = title.strip()
    if URL_PREFIX.search(value) or DOMAIN_PATH.search(value):
        return True
    return value.count("/") >= 2 or bool(re.search(r"/(?:jobs?|careers?)/", value, re.I))


def is_aggregator_title(title: str) -> bool:
    """Identify search-page headings that do not name one individual role."""

    return bool(AGGREGATOR_TITLE.search(" ".join(title.split())))


def is_clean_posting_title(title: str) -> bool:
    """Apply the narrow posting-title quality gate used after segmentation."""

    value = " ".join(title.split())
    return (
        bool(value)
        and len(value) <= 180
        and not (is_url_like_title(value) or is_aggregator_title(value))
    )


def title_is_grounded(title: str, posting_segment: str) -> bool:
    """Require a normalized title-equivalent span inside posting-specific text."""

    candidate = normalized_comparison(title)
    source = normalized_comparison(posting_segment)
    if not candidate or not source:
        return False
    return bool(re.search(rf"(?:^|\s){re.escape(candidate)}(?:\s|$)", source))


def title_is_relevant(candidate_title: str, target_title: str) -> bool:
    candidate = normalized_comparison(candidate_title)
    target = normalized_comparison(target_title)
    if candidate == target:
        return True
    candidate_tokens = set(candidate.split())
    target_tokens = set(target.split())
    if not (candidate_tokens & target_tokens & ROLE_WORDS):
        return False
    target_subjects = target_tokens - ROLE_WORDS - {"senior", "junior", "solutions", "solution"}
    if candidate_tokens & target_subjects:
        return True
    return "ai" in target_tokens and any("ai" in token for token in candidate_tokens)


def compatible_role_heading(candidate_title: str, target_title: str) -> bool:
    """A discovery candidate, not proof of specialty, level or candidate fit.

    Developer/software-engineer is a functional alias, not an alias for every
    engineering occupation. Other functions must share their occupational head.
    """
    candidate = set(normalized_comparison(candidate_title).split())
    target = set(normalized_comparison(target_title).split())
    candidate_heads = candidate & ROLE_WORDS
    target_heads = target & ROLE_WORDS
    # Do not silently collapse individual contribution into management/architecture.
    authority = {"manager", "director", "lead", "architect"}
    if (candidate_heads & authority) != (target_heads & authority):
        return False
    if candidate_heads & target_heads:
        return True
    software_candidate = "developer" in candidate or {"software", "engineer"} <= candidate
    software_target = "developer" in target or {"software", "engineer"} <= target
    return software_candidate and software_target


def body_supported_specialty(candidate_title: str, target_title: str, body: str) -> bool:
    """Let substantive work/qualification text establish a missing title specialty.

    This only admits a target variant for extraction. The batch model must still
    separate specialist conditions and reject materially different role scopes.
    Never infer specialty from benefits, employer marketing, negation or preferences.
    """
    if not body or not compatible_role_heading(candidate_title, target_title):
        return False
    rank_words = {"senior", "junior", "staff", "principal", "intern", "internship"}
    candidate = set(normalized_comparison(candidate_title).split())
    target = set(normalized_comparison(target_title).split())
    if candidate & rank_words != target & rank_words:
        return False
    subjects = target - ROLE_WORDS - rank_words - {"solution", "and", "of", "the"}
    if not subjects:
        return False
    # This rescue fills a missing specialty; it must not erase an explicitly
    # different specialization already present alongside the target in a title.
    neutral_scope_words = {"software", "full", "stack", "fullstack", "application", "applications"}
    if subjects <= candidate and candidate - target - neutral_scope_words:
        return False
    section = ""
    cue = ""
    supported = set()
    for raw_line in body.splitlines():
        line = normalized_comparison(raw_line)
        if not line:
            continue
        if len(line.split()) <= 12:
            if re.search(r"\b(?:preferred|bonus|nice to have|good to have)\b", line):
                section, cue = "preference", ""
            elif re.search(
                r"\b(?:benefits|compensation|about us|about the company|salary|perks)\b", line
            ):
                section, cue = "metadata", ""
            elif re.search(
                r"\b(?:qualifications|requirements|required|must have|mandatory skills|"
                r"what we re looking for|what you bring)\b",
                line,
            ):
                section, cue = "hiring", ""
            elif re.search(
                r"\b(?:responsibilities|what you ll do|what you ll build|duties)\b", line
            ):
                section, cue = "work", ""
        if re.search(
            r"\b(?:not required|no experience|do not use|don t use|no longer|"
            r"migrat\w* away|preferred|bonus|nice to have|good to have)\b",
            line,
        ):
            continue
        if section in {"preference", "metadata"}:
            continue
        if re.search(
            r"\b(?:experience|expertise|proficiency|proficient|programming|develop\w*|"
            r"build\w*|design\w*|maintain\w*|using|knowledge|mandatory|required|skills)\b",
            line,
        ):
            cue = line
        tokens = set(line.split())
        # A short list item inherits the active qualification/work section; a
        # standalone keyword without such context cannot establish role relevance.
        if section in {"hiring", "work"} or cue == line or (cue and len(tokens) <= 6):
            supported.update(subjects & tokens)
    return subjects <= supported


def is_promising_search_result(result: MarketSearchResult, target_title: str) -> bool:
    combined = " ".join([result.title, result.url, *result.snippets]).casefold()
    if any(pattern in combined for pattern in REJECT_PATTERNS):
        return False
    if not (
        title_is_relevant(result.title, target_title)
        or compatible_role_heading(result.title, target_title)
    ):
        return False
    return looks_like_individual_job_url(result.url) or any(
        signal in combined for signal in HIRING_SIGNALS
    )


def is_plausible_current_job_page(
    result: MarketSearchResult,
    page: MarketPageContent,
    target_title: str,
) -> bool:
    combined = " ".join(
        [result.title, result.url, *result.snippets, page.title or "", page.markdown]
    )
    folded = combined.casefold()
    if any(pattern in folded for pattern in REJECT_PATTERNS):
        return False
    if not (
        title_is_relevant(page.title or result.title, target_title)
        or body_supported_specialty(page.title or result.title, target_title, page.markdown)
    ):
        return False
    if not any(signal in folded for signal in HIRING_SIGNALS):
        return False
    expired_signals = re.search(r"\b(job|position|posting) (is )?(closed|expired|filled)\b", folded)
    return expired_signals is None


def is_exact_title(candidate_title: str, search_title: str) -> bool:
    return _strict_title_key(candidate_title) == _strict_title_key(search_title)


def _strict_title_key(value: str) -> str:
    """Normalize punctuation while preserving lexical title distinctions."""

    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def target_title_variants(target_title: str) -> list[str]:
    """Generate a small deterministic lexical-variant set for a confirmed title."""

    title = " ".join(target_title.split())
    variants: list[str] = []
    for long_form, short_form in (("Senior", "Sr."), ("Junior", "Jr.")):
        if re.search(rf"\b{long_form}\b", title, re.I):
            variants.append(re.sub(rf"\b{long_form}\b", short_form, title, flags=re.I))
        elif re.search(rf"\b{short_form[:2]}\.?\s", title, re.I):
            variants.append(re.sub(rf"\b{short_form[:2]}\.?", long_form, title, flags=re.I))
    if re.search(r"\bSolutions\b", title, re.IGNORECASE):
        variants.append(re.sub(r"\bSolutions\b", "Solution", title, count=1, flags=re.I))
    elif re.search(r"\bSolution\b", title, re.IGNORECASE):
        variants.append(re.sub(r"\bSolution\b", "Solutions", title, count=1, flags=re.I))

    if re.match(r"^AI\s+", title, re.IGNORECASE):
        remainder = re.sub(r"^AI\s+", "", title, count=1, flags=re.I)
        variants.extend(
            [
                f"AI/ML {remainder}",
                f"Generative AI {remainder}",
                f"GenAI {remainder}",
            ]
        )
    elif re.match(r"^Generative AI\s+", title, re.IGNORECASE):
        remainder = re.sub(r"^Generative AI\s+", "", title, count=1, flags=re.I)
        variants.append(f"GenAI {remainder}")
    elif re.match(r"^GenAI\s+", title, re.IGNORECASE):
        remainder = re.sub(r"^GenAI\s+", "", title, count=1, flags=re.I)
        variants.append(f"Generative AI {remainder}")

    exact_key = _strict_title_key(title)
    unique: dict[str, str] = {}
    for variant in variants:
        key = _strict_title_key(variant)
        if key != exact_key:
            unique.setdefault(key, variant)
    return list(unique.values())


def title_equivalence_reason(
    candidate_title: str, target_title: str, posting_text: str | None = None
) -> str | None:
    """Explain equivalent wording without erasing role or seniority distinctions."""
    if is_exact_title(candidate_title, target_title):
        return "LITERAL_EXACT"
    if normalized_comparison(candidate_title) == normalized_comparison(target_title):
        return "LEXICAL_EQUIVALENCE"
    if not posting_text:
        return None
    parts = re.split(r"\s+[—–|\-]\s+", candidate_title, maxsplit=1)
    if len(parts) != 2 or normalized_comparison(parts[0]) != normalized_comparison(target_title):
        return (
            "DESCRIPTION_SUPPORTED_SPECIALTY"
            if body_supported_specialty(candidate_title, target_title, posting_text)
            else None
        )
    # A suffix describing authority/function/level must never be discarded as decoration.
    if re.search(
        r"\b(?:lead|manager|management|director|head|staff|principal|chief|supervisor|"
        r"junior|senior|intern|architect|analyst|consultant|engineer|developer)\b",
        parts[1],
        re.I,
    ):
        return None
    body = normalized_comparison(posting_text)
    body = body.replace(normalized_comparison(candidate_title), "")
    suffix = set(normalized_comparison(parts[1]).split()) - {"and", "with", "in", "using"}
    body_tokens = set(body.split())
    descriptor_supported = all(
        token in body_tokens
        or (token.endswith("s") and len(token) > 3 and token[:-1] in body_tokens)
        or f"{token}s" in body_tokens
        for token in suffix
    )
    # The exact base title establishes role and level. A descriptor must also occur
    # independently in substantive work/qualification text, not only in that heading.
    # The body need not repeat the entire job title a second time (many employers do not).
    has_work_context = bool(
        re.search(
            r"\b(?:qualifications|requirements|skills|experience|responsibilities|duties|"
            r"stack|technologies|technology|using|provides|develop|work with)\b",
            body,
        )
    )
    if suffix and len(suffix) <= 8 and descriptor_supported and has_work_context:
        return "DESCRIPTIVE_SUFFIX_GROUNDED"
    return None


def is_target_title_variant(
    candidate_title: str, target_title: str, posting_text: str | None = None
) -> bool:
    if title_equivalence_reason(candidate_title, target_title, posting_text):
        return not is_exact_title(candidate_title, target_title)
    candidate = _strict_title_key(candidate_title)
    return candidate in {
        _strict_title_key(variant) for variant in target_title_variants(target_title)
    }


def observed_related_titles(titles: list[str], target_title: str, *, limit: int) -> list[str]:
    """Return only clean, posting-grounded titles observed during source processing."""

    related: dict[str, str] = {}
    for title in titles:
        key = normalized_comparison(title)
        if (
            is_clean_posting_title(title)
            and not is_exact_title(title, target_title)
            and not is_target_title_variant(title, target_title)
            and title_is_relevant(title, target_title)
            and key not in related
        ):
            related[key] = title.strip()
    return [related[key] for key in sorted(related)[:limit]]
