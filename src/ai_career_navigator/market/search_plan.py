"""Deterministic V1 market-search planning."""

from ai_career_navigator.domain import ApprovalStatus, CareerGoal, GeographyScope
from ai_career_navigator.market.errors import MarketConfigurationError
from ai_career_navigator.market.schemas import (
    GeographyQueryVariant,
    SearchPlan,
    SearchPlanStatus,
)
from ai_career_navigator.market.validation import target_title_variants


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split())
    return normalized or None


def _search_title(goal: CareerGoal) -> str:
    role = _clean(goal.target_role) or ""
    seniority = _clean(goal.target_seniority)
    if seniority and seniority.casefold() not in role.casefold():
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
    early_career_markers = {
        "intern",
        "internship",
        "junior",
        "entry level",
        "new grad",
        "new graduate",
        "graduate",
    }
    return not any(marker in target for marker in early_career_markers)


def _internship_suffix(target_role: str, target_seniority: str | None) -> str:
    return " -intern -internship" if _exclude_internships(target_role, target_seniority) else ""


def build_you_ats_query(
    target_role: str, geography: str, target_seniority: str | None = None
) -> str:
    """Build the single primary You.com query for individual ATS postings."""

    role = " ".join(target_role.replace('"', "").split())
    location = " ".join(geography.replace('"', "").split())
    return (
        f'"{role}" {location} '
        "(site:boards.greenhouse.io OR site:jobs.lever.co OR "
        "site:jobs.ashbyhq.com OR site:myworkdayjobs.com)"
        f"{_internship_suffix(role, target_seniority)}"
    )


def build_you_fallback_query(
    target_role: str, geography: str, target_seniority: str | None = None
) -> str:
    """Build one bounded fallback that still asks for individual employer postings."""

    role = " ".join(target_role.replace('"', "").split())
    location = " ".join(geography.replace('"', "").split())
    return (
        f'"{role}" {location} (careers OR jobs)'
        f"{_internship_suffix(role, target_seniority)}"
    )
