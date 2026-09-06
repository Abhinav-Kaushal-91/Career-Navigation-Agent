"""Explainable deterministic validation for candidate job pages."""

import re

from ai_career_navigator.market.normalization import normalized_comparison
from ai_career_navigator.market.schemas import MarketPageContent, MarketSearchResult

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
JOB_URL_SIGNALS = (
    "/job/",
    "/jobs/",
    "/careers/",
    "greenhouse.io",
    "lever.co",
    "myworkdayjobs.com",
    "smartrecruiters.com",
    "workable.com",
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


def is_promising_search_result(result: MarketSearchResult, target_title: str) -> bool:
    combined = " ".join([result.title, result.url, *result.snippets]).casefold()
    if any(pattern in combined for pattern in REJECT_PATTERNS):
        return False
    if not title_is_relevant(result.title, target_title):
        return False
    return any(signal in combined for signal in JOB_URL_SIGNALS + HIRING_SIGNALS)


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
    if not title_is_relevant(page.title or result.title, target_title):
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


def is_target_title_variant(candidate_title: str, target_title: str) -> bool:
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
