"""Offline ATS query contracts; no live provider calls or relaxed validation."""

import asyncio
from datetime import UTC, datetime

import pytest

from ai_career_navigator.domain import ApprovalStatus, CareerGoal, GeographyScope, GoalType
from ai_career_navigator.market.mcp.you_client import YouMcpMarketSearchClient
from ai_career_navigator.market.schemas import SearchFreshness, SearchLimits, SearchPassType
from ai_career_navigator.market.search_plan import (
    build_search_plan,
    build_you_ats_query,
    build_you_query_family,
)
from ai_career_navigator.market.source_registry import (
    AGGREGATOR_SEARCH_DOMAINS,
    ATS_JOB_SEARCH_DOMAINS,
    is_ats_domain,
)


def _requests(role="Senior Java Developer", **overrides):
    values = {
        "target_role": role,
        "target_location": "Toronto, Canada",
        "goal_type": GoalType.TARGET_CAREER_PATH,
        "geography_scopes": [GeographyScope.STRICT_CITY],
        "approval_status": ApprovalStatus.APPROVED,
        "approved_at": datetime(2026, 9, 7, tzinfo=UTC),
    }
    values.update(overrides)
    return build_you_query_family(build_search_plan(CareerGoal(**values)))


def test_three_complementary_passes_use_strict_ats_and_open_employer_discovery():
    requests = _requests()
    assert len(requests) == 3
    assert len({request.query for request in requests}) == 3
    assert [request.pass_type for request in requests] == [
        SearchPassType.ATS_PRIMARY,
        SearchPassType.ATS_FALLBACK,
        SearchPassType.TARGET_VARIANT,
    ]
    for request in (requests[0], requests[2]):
        assert set(request.included_domains) == ATS_JOB_SEARCH_DOMAINS
        assert not request.boosted_domains
        assert not request.excluded_domains  # Provider rejects allowlist + exclude/boost.
    assert set(requests[1].excluded_domains) == AGGREGATOR_SEARCH_DOMAINS
    assert not requests[1].included_domains
    assert "apply" in requests[1].query
    assert all('"Toronto" Canada' in request.query for request in requests)
    assert all(request.geography_scope is GeographyScope.STRICT_CITY for request in requests)
    assert all(request.country == "CA" for request in requests)
    assert all(request.count == 12 for request in requests)


def test_later_passes_widen_index_lookback_without_changing_posting_currentness_window():
    requests = _requests()
    assert [request.freshness for request in requests] == [
        SearchFreshness.MONTH,
        SearchFreshness.YEAR,
        SearchFreshness.YEAR,
    ]
    assert SearchLimits().max_posting_age_days == 90


@pytest.mark.parametrize(
    ("geography", "scope", "expected"),
    [
        ("Toronto, Canada", GeographyScope.STRICT_CITY, '"Toronto" Canada'),
        (
            "New Westminster, British Columbia, Canada",
            GeographyScope.STRICT_CITY,
            '"New Westminster" British Columbia Canada',
        ),
        ("British Columbia, Canada", GeographyScope.PROVINCE, '"British Columbia" Canada'),
        ("Canada", GeographyScope.COUNTRY, '"Canada"'),
    ],
)
def test_geography_phrase_preserves_supplied_city_province_or_country(geography, scope, expected):
    requests = _requests(target_location=geography, geography_scopes=[scope])
    assert all(expected in request.query for request in requests)
    assert all(request.geography_scope is scope for request in requests)


def test_ats_search_hosts_span_existing_providers_without_vendor_marketing_roots():
    assert len(ATS_JOB_SEARCH_DOMAINS) >= 6
    assert all(is_ats_domain(domain) for domain in ATS_JOB_SEARCH_DOMAINS)
    assert not {"greenhouse.io", "lever.co", "workable.com"} & ATS_JOB_SEARCH_DOMAINS
    assert "job-boards.greenhouse.io" in ATS_JOB_SEARCH_DOMAINS


@pytest.mark.parametrize(
    "role", ["AI Engineer", "Product Manager", "Registered Nurse", "Accountant"]
)
def test_non_lexical_specialties_are_not_invented_for_equivalent_query(role):
    requests = _requests(role)
    assert requests[0].query.startswith(f'"{role}"')
    assert requests[2].query.startswith(f'{role} "Toronto"')
    assert all(
        "AI/ML" not in request.query and "GenAI" not in request.query for request in requests
    )
    assert all("Spring" not in request.query and "AWS" not in request.query for request in requests)


@pytest.mark.parametrize(
    ("role", "seniority", "variant"),
    [
        ("Java Developer", "Senior", "Sr. Java Developer"),
        ("Business Analyst", "Junior", "Jr. Business Analyst"),
        ("Solutions Architect", None, "Solution Architect"),
    ],
)
def test_safe_lexical_variant_preserves_explicit_seniority_and_target(role, seniority, variant):
    assert _requests(role, target_seniority=seniority)[2].query.startswith(f'"{variant}"')


@pytest.mark.parametrize("role", ["Internal Auditor", "International Sales Manager"])
def test_internal_and_international_are_not_internship_targets(role):
    assert build_you_ats_query(role, "Toronto").endswith("-intern -internship")


@pytest.mark.parametrize("role", ["Jr. Analyst", "Junior Analyst", "Entry-level Analyst", "Intern"])
def test_explicit_early_career_targets_keep_internship_discovery(role):
    assert all("-intern" not in request.query for request in _requests(role))


@pytest.mark.parametrize("supports_filters", [True, False])
def test_effective_mcp_queries_keep_domain_constraints_when_filter_fields_are_unavailable(
    monkeypatch, supports_filters
):
    client = YouMcpMarketSearchClient(
        endpoint="https://api.you.com/mcp", api_key="synthetic", timeout_seconds=1
    )
    client._search_properties = (
        {"query", "include_domains", "exclude_domains", "boost_domains"}
        if supports_filters
        else {"query"}
    )
    observed = []

    async def capture(tool, arguments):
        assert tool == "you-search"
        observed.append(arguments)
        return {"results": {"web": []}}

    monkeypatch.setattr(client, "_call", capture)
    for request in _requests():
        asyncio.run(client.search(request))
    for index, arguments in enumerate(observed):
        assert '"Toronto" Canada' in arguments["query"]
        assert "boost_domains" not in arguments
        if supports_filters:
            if index == 1:
                assert "indeed.com" in arguments["exclude_domains"]
                assert "include_domains" not in arguments
            else:
                assert set(arguments["include_domains"]) == ATS_JOB_SEARCH_DOMAINS
                assert "exclude_domains" not in arguments
        elif index == 1:
            assert "-site:indeed.com" in arguments["query"]
            assert "-site:jooble.org" in arguments["query"]
        else:
            assert "site:boards.greenhouse.io" in arguments["query"]
            assert "site:apply.workable.com" in arguments["query"]
