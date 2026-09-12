"""Deterministic V1 market-search planning."""

import re

from ai_career_navigator.domain import ApprovalStatus, CareerGoal, GeographyScope
from ai_career_navigator.market.errors import MarketConfigurationError
from ai_career_navigator.market.normalization import normalize_title, normalized_comparison
from ai_career_navigator.market.schemas import (
    GeographyQueryVariant,
    MarketSearchRequest,
    SearchFreshness,
    SearchPassType,
    SearchPlan,
    SearchPlanStatus,
)
from ai_career_navigator.market.source_registry import (
    AGGREGATOR_SEARCH_DOMAINS,
    ATS_JOB_SEARCH_DOMAINS,
)
from ai_career_navigator.market.validation import body_supported_specialty, target_title_variants


def leadership_domain_priority(target_role: str, title: str, body: str) -> int:
    """Order leadership discovery, never infer equivalence or discard a missing keyword.

    Shared words such as 'engineering manager' do not establish a discipline.
    A generic heading may still establish the target discipline in its actual work.
    Unconfirmed domains stay last for model scope review, not automatic gap creation.
    """
    generic = {
        "engineer", "engineering", "manager", "management", "director", "head",
        "lead", "leader", "leadership", "team", "senior", "junior", "staff",
        "principal", "chief", "vp", "vice", "president", "of", "the", "and",
    }
    subjects = set(normalized_comparison(target_role).split()) - generic
    if not subjects or subjects <= set(normalized_comparison(title).split()):
        return 0
    # Reuse substantive work/qualification grounding, not employer marketing.
    # The synthetic shared head only checks domain text, not seniority equivalence.
    if body_supported_specialty("Manager", " ".join(sorted(subjects)) + " Manager", body):
        return 1
    return 2


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split())
    return normalized or None


def _search_title(goal: CareerGoal) -> str:
    role = _clean(goal.target_role) or ""
    seniority = _clean(goal.target_seniority)
    if seniority and normalize_title(seniority).casefold() not in normalize_title(role).casefold():
        return f"{seniority} {role}"
    return role


def _geography_phrases(goal: CareerGoal, geography: str) -> list[tuple[GeographyScope, str]]:
    default_scope = (
        GeographyScope.COUNTRY if geography.casefold() == "canada" else GeographyScope.STRICT_CITY
    )
    allowed = goal.geography_scopes or [default_scope]
    folded = geography.casefold()
    phrases: list[tuple[GeographyScope, str]] = []
    for scope in allowed:
        if "toronto" in folded:
            if scope is GeographyScope.STRICT_CITY:
                phrases.extend(
                    [
                        (scope, '"Toronto, ON"'),
                        (scope, "Toronto Ontario"),
                    ]
                )
            elif scope is GeographyScope.METRO_AREA:
                phrases.extend(
                    [
                        (scope, '"Greater Toronto Area"'),
                        (scope, "Mississauga Ontario"),
                        (scope, "Markham Ontario"),
                    ]
                )
            elif scope is GeographyScope.PROVINCE:
                phrases.append((scope, "Ontario Canada"))
            elif scope is GeographyScope.COUNTRY:
                phrases.append((scope, "Canada"))
            elif scope is GeographyScope.COUNTRY_REMOTE:
                phrases.append((scope, "remote Canada"))
        else:
            phrase = "Canada" if scope is GeographyScope.COUNTRY else geography.replace(",", "")
            if scope is GeographyScope.COUNTRY_REMOTE:
                phrase = f"remote {phrase}"
            phrases.append((scope, phrase))
    return phrases


def build_search_plan(goal: CareerGoal) -> SearchPlan:
    """Build a stable exact-title-first plan from an approved career goal."""

    if goal.approval_status is not ApprovalStatus.APPROVED:
        raise MarketConfigurationError("market search requires an approved career goal")

    geography = _clean(goal.target_location) or "Location not specified"
    if not _clean(goal.target_role):
        return SearchPlan(
            status=SearchPlanStatus.SEARCH_PLAN_REQUIRES_ROLE_DISCOVERY,
            goal_type=goal.goal_type,
            geography=geography,
            preferred_work_modes=goal.preferred_work_modes,
            target_industries=goal.target_industries,
            exclusions=goal.exclusions,
            expansion_permitted=goal.search_expansion_permission,
        )

    title = _search_title(goal)
    clean_title = title.replace(chr(34), "")
    geography_phrases = _geography_phrases(goal, geography)
    geography_queries = [
        GeographyQueryVariant(
            scope=scope,
            location_phrase=phrase,
            direct_source_query=f'"{clean_title}" {phrase} careers',
            general_query=f'"{clean_title}" jobs {phrase}',
        )
        for scope, phrase in geography_phrases
    ]
    default_scope = (
        GeographyScope.COUNTRY if geography.casefold() == "canada" else GeographyScope.STRICT_CITY
    )
    allowed_scopes = list(dict.fromkeys(goal.geography_scopes)) or [default_scope]
    return SearchPlan(
        status=SearchPlanStatus.READY,
        goal_type=goal.goal_type,
        target_role=_clean(goal.target_role),
        search_title=title,
        target_seniority=_clean(goal.target_seniority),
        geography=geography,
        preferred_work_modes=goal.preferred_work_modes,
        target_industries=goal.target_industries,
        exclusions=goal.exclusions,
        expansion_permitted=goal.search_expansion_permission,
        target_title_variants=target_title_variants(title),
        allowed_geography_scopes=allowed_scopes,
        geography_queries=geography_queries,
        direct_source_queries=[item.direct_source_query for item in geography_queries],
        exact_queries=[item.general_query for item in geography_queries],
    )


def build_related_query(title: str, geography: str) -> str:
    normalized = " ".join(title.replace('"', "").split())
    search_geography = geography.replace(",", "")
    location_suffix = "" if geography == "Location not specified" else f" {search_geography}"
    return f'"{normalized}" jobs{location_suffix}'


def _exclude_internships(target_role: str, target_seniority: str | None) -> bool:
    """Use only target-role inputs to decide whether early-career evidence is eligible."""

    target = f"{target_seniority or ''} {target_role}".casefold().replace("-", " ")
    # Substrings such as "intern" in "Internal Auditor" are not career stages.
    return (
        re.search(
            r"\b(?:intern|internship|junior|jr\.?|entry level|new grad|new graduate|graduate)\b",
            target,
        )
        is None
    )


def _internship_suffix(target_role: str, target_seniority: str | None) -> str:
    return " -intern -internship" if _exclude_internships(target_role, target_seniority) else ""


def _you_location_query(geography: str) -> str:
    """Keep the user-supplied locality together without inventing a broader area."""
    parts = [
        cleaned
        for part in geography.replace('"', "").split(",")
        if (cleaned := " ".join(part.split()))
    ]
    if not parts:
        return ""
    return " ".join([f'"{parts[0]}"', *parts[1:]])


def build_you_ats_query(
    target_role: str, geography: str, target_seniority: str | None = None
) -> str:
    """Build the single primary You.com query for individual ATS postings."""

    role = " ".join(target_role.replace('"', "").split())
    location = _you_location_query(geography)
    domains = " OR ".join(f"site:{domain}" for domain in sorted(ATS_JOB_SEARCH_DOMAINS))
    return f'"{role}" {location} ({domains}){_internship_suffix(role, target_seniority)}'


def build_you_fallback_query(
    target_role: str, geography: str, target_seniority: str | None = None
) -> str:
    """Build one bounded fallback that still asks for individual employer postings."""

    role = " ".join(target_role.replace('"', "").split())
    location = _you_location_query(geography)
    return (
        f'"{role}" {location} (apply OR "job description")'
        f"{_internship_suffix(role, target_seniority)}"
    )


def _lexical_query_variant(role: str) -> str | None:
    """Allow wording changes, not a wider specialty or a new target function."""

    def lexical_key(title: str) -> str:
        value = re.sub(r"\bsr\.?\b", "senior", title, flags=re.I)
        value = re.sub(r"\bjr\.?\b", "junior", value, flags=re.I)
        value = re.sub(r"\bsolutions\b", "solution", value, flags=re.I)
        return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))

    role_key = lexical_key(role)
    return next(
        (variant for variant in target_title_variants(role) if lexical_key(variant) == role_key),
        None,
    )


def build_you_query_family(plan: SearchPlan) -> list[MarketSearchRequest]:
    """Three complementary passes within the existing shared discovery budget.

    ATS allowlists are strict, not optional ranking boosts. The middle pass keeps
    custom employer career sites discoverable without reintroducing aggregators.
    Later passes widen search-index lookback, not acceptable posting age. All
    candidates still pass the same role, seniority, geography and currentness checks.
    """
    role = " ".join((plan.search_title or plan.target_role or "").replace('"', "").split())
    geography = plan.geography if plan.geography != "Location not specified" else "Canada"
    location = _you_location_query(geography)
    suffix = _internship_suffix(role, plan.target_seniority)
    common = {"geography_scope": plan.allowed_geography_scopes[0]}
    queries = [
        MarketSearchRequest(
            query=f'"{role}" {location}{suffix}',
            pass_type=SearchPassType.ATS_PRIMARY,
            freshness=SearchFreshness.MONTH,
            included_domains=sorted(ATS_JOB_SEARCH_DOMAINS),
            **common,
        ),
        MarketSearchRequest(
            query=build_you_fallback_query(role, geography, plan.target_seniority),
            pass_type=SearchPassType.ATS_FALLBACK,
            freshness=SearchFreshness.YEAR,
            excluded_domains=sorted(AGGREGATOR_SEARCH_DOMAINS),
            **common,
        ),
    ]
    equivalent = _lexical_query_variant(role)
    # Without a lexical variant, retry the same title's words without a phrase
    # constraint. This improves discovery recall without adding skills or roles.
    title_query = f'"{equivalent}"' if equivalent else role
    queries.append(
        MarketSearchRequest(
            query=f"{title_query} {location} (apply OR qualifications OR responsibilities){suffix}",
            pass_type=SearchPassType.TARGET_VARIANT,
            freshness=SearchFreshness.YEAR,
            included_domains=sorted(ATS_JOB_SEARCH_DOMAINS),
            **common,
        )
    )
    return queries
