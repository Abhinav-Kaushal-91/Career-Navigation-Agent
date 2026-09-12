"""JSearch integration tests never spend API quota."""

import asyncio

import httpx
import pytest

from ai_career_navigator.config import Settings
from ai_career_navigator.market.errors import MarketAuthenticationError, MarketRateLimitError
from ai_career_navigator.market.factory import build_primary_market_client
from ai_career_navigator.market.jsearch_client import JSearchMarketClient, normalize_jsearch_payload
from ai_career_navigator.market.jsearch_service import retrieve_jsearch_market
from tests.market.test_combined_service import NOW, goal


def raw(index="1", description="Design AI services. Python experience required."):
    return dict(
        job_id=index,
        job_title="AI Solutions Architect",
        employer_name="Example",
        job_apply_link=f"https://example.org/jobs/{index}",
        job_description=description,
        job_city="Toronto",
        job_state="Ontario",
        job_country="CA",
        job_posted_at_datetime_utc="2026-09-01T00:00:00Z",
    )


def client(handler, **kwargs):
    return JSearchMarketClient(
        api_key="private-test-token", transport=httpx.MockTransport(handler), **kwargs
    )


@pytest.mark.parametrize("target", ["Software Engineering Manager", "Finance Manager"])
def test_leadership_search_uses_chosen_destination_without_inheriting_current_role(target):
    requests = []

    def handler(request):
        requests.append(request)
        assert request.url.path == "/search-v2"
        assert dict(request.url.params) == {
            "query": f"{target} in toronto, canada",
            "country": "canada",
            "language": "en",
            "date_posted": "all",
            "num_pages": "1",
        }
        return httpx.Response(200, json={"status": "OK", "data": []})

    destination = goal().model_copy(update={
        "goal_type": "LEADERSHIP_PROGRESSION",
        "target_role": target,
        "target_seniority": None,
        "target_location": "Toronto, Canada",
    })
    asyncio.run(retrieve_jsearch_market(destination, client(handler), now=NOW))
    assert len(requests) == 1


@pytest.mark.parametrize("target,title,body,priority", [
    ("Software Engineering Manager", "Software Development Manager", "", 0),
    ("Software Engineering Manager", "Engineering Manager",
     "Responsibilities\nLead software delivery and develop engineering teams.", 1),
    ("Software Engineering Manager", "Manufacturing Engineering Manager",
     "Responsibilities\nManage factory tooling and manufacturing schedules.", 2),
    ("Software Engineering Manager", "Engineering Manager",
     "About the company\nWe sell software to manufacturers.", 2),
    ("Finance Manager", "Operations Manager",
     "Requirements\nExperience leading finance teams is required.", 1),
])
def test_leadership_domain_ranking_is_generic_and_body_aware(target, title, body, priority):
    from ai_career_navigator.market.search_plan import leadership_domain_priority

    assert leadership_domain_priority(target, title, body) == priority


def test_normalizes_both_endpoint_envelopes_without_assuming_complete():
    for data in ([raw()], {"jobs": [raw()], "cursor": "next"}):
        page = normalize_jsearch_payload({"status": "OK", "data": data})
        assert page.results[0].provider == "JSEARCH"
        assert page.results[0].location == "Toronto, Ontario, Canada"
        assert page.results[0].content_complete is None


def test_one_search_with_existing_descriptions_never_fetches_details():
    requests = []

    def handler(request):
        requests.append(request)
        assert request.headers["x-rapidapi-key"] == "private-test-token"
        assert request.headers["x-rapidapi-host"] == "jsearch.p.rapidapi.com"
        assert request.url.params["country"] == "canada"
        assert request.url.params["query"] == "AI Solutions Architect in canada"
        assert request.url.params["date_posted"] == "all"
        assert request.url.params["num_pages"] == "1"
        assert "cursor" not in request.url.params
        return httpx.Response(200, json={"status": "OK", "data": {"jobs": [raw(), raw("2")]}})

    result = asyncio.run(retrieve_jsearch_market(goal(), client(handler), now=NOW))
    assert len(requests) == 1
    assert result.snapshot.validated_posting_count == 2
    assert result.primary_provider == "JSEARCH"
    assert result.enrichment_provider is None
    assert result.enrichment_attempt_count == 0
    assert result.you_search_count == 0
    assert all(item.primary_source.source_type == "JSEARCH" for item in result.posting_evidence)
    assert "private-test-token" not in result.model_dump_json()


def test_missing_descriptions_use_matching_details_once_and_respect_budget():
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path == "/search-v2":
            return httpx.Response(
                200,
                json={
                    "status": "OK",
                    "data": [raw("1", ""), raw("1", ""), raw("2", ""), raw("3", "")],
                },
            )
        assert request.url.params["job_id"] == "1"
        return httpx.Response(200, json={"status": "OK", "data": [raw()]})

    result = asyncio.run(retrieve_jsearch_market(goal(), client(handler, max_details=1), now=NOW))
    assert len(requests) == 2
    assert result.enrichment_attempt_count == result.enrichment_success_count == 1
    assert result.budget_deferred_result_count == 2
    assert len(result.postings) == 3
    assert result.posting_evidence[0].primary_content.markdown == raw()["job_description"]


def test_search_matches_successful_toronto_probe_without_cursor():
    from ai_career_navigator.market.schemas import StructuredJobSearchRequest

    def handler(request):
        assert dict(request.url.params) == {
            "query": "Senior Java developer in toronto, canada",
            "country": "canada",
            "language": "en",
            "date_posted": "all",
            "num_pages": "1",
        }
        return httpx.Response(200, json={"status": "OK", "data": []})

    async def run():
        async with client(handler) as api:
            await api.search_page(
                StructuredJobSearchRequest(
                    title="Senior Java developer", location="Toronto, Canada", country="ca"
                )
            )

    asyncio.run(run())


@pytest.mark.parametrize(
    "status,error",
    [
        (401, MarketAuthenticationError),
        (403, MarketAuthenticationError),
        (429, MarketRateLimitError),
    ],
)
def test_auth_and_quota_errors_are_safe_and_never_retried(status, error):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(status, text="private-test-token")

    with pytest.raises(error) as caught:
        asyncio.run(retrieve_jsearch_market(goal(), client(handler), now=NOW))
    assert len(requests) == 1
    assert "private-test-token" not in str(caught.value)


def test_details_cannot_substitute_a_different_job():
    def handler(request):
        jobs = [raw("1", "")] if request.url.path == "/search-v2" else [raw("other")]
        return httpx.Response(200, json={"status": "OK", "data": jobs})

    result = asyncio.run(retrieve_jsearch_market(goal(), client(handler), now=NOW))
    assert result.enrichment_success_count == 0
    assert result.posting_evidence[0].primary_content.markdown == ""


def test_expired_and_out_of_scope_jobs_are_not_retained():
    closed = raw("closed") | {"job_offer_expiration_datetime_utc": "2026-01-01T00:00:00Z"}
    abroad = raw("abroad") | {"job_city": "Chicago", "job_state": "Illinois", "job_country": "US"}

    def handler(request):
        return httpx.Response(200, json={"status": "OK", "data": [closed, abroad]})

    result = asyncio.run(retrieve_jsearch_market(goal(), client(handler), now=NOW))
    assert not result.postings
    assert result.rejected_result_count == 2


def test_factory_can_build_without_either_legacy_key():
    settings = Settings(_env_file=None, rapidapi_key="private-test-token")
    result = build_primary_market_client(settings)
    assert isinstance(result, JSearchMarketClient)
    assert "private-test-token" not in repr(result)


@pytest.mark.parametrize("include_target", [True, False])
def test_unrelated_discoveries_are_audited_but_not_sent_to_analysis(include_target):
    unrelated = raw("unrelated", "Prepare meals and maintain kitchen hygiene.") | {
        "job_title": "Executive Chef",
        "employer_name": "Restaurant",
    }
    jobs = ([raw()] if include_target else []) + [unrelated]

    def handler(request):
        return httpx.Response(200, json={"status": "OK", "data": jobs})

    result = asyncio.run(retrieve_jsearch_market(goal(), client(handler), now=NOW))
    expected = int(include_target)
    assert result.raw_source_count == len(jobs)
    assert len(result.posting_audits) == len(jobs)
    assert result.rejected_result_count == 1
    audit = next(a for a in result.posting_audits if a.parent_result_id == "unrelated")
    assert audit.title == "Executive Chef"
    assert audit.title_classification == "IRRELEVANT"
    assert audit.rejection_reason == "Outside target-role cohort: unrelated role classification"
    assert not audit.selected_for_primary_evidence
    assert len(result.postings) == len(result.posting_evidence) == expected
    assert len(result.sources) == len(result.source_contents) == expected
    assert result.total_unique_retained_posting_count == expected
    snapshot = result.snapshot
    assert snapshot.validated_posting_count == expected
    assert (
        snapshot.exact_title_count + snapshot.target_variant_count + snapshot.related_title_count
    ) == expected
    assert "Restaurant" not in snapshot.employer_posting_counts
    assert all("kitchen" not in e.primary_content.markdown for e in result.posting_evidence)


def test_summary_preserves_selected_classification_instead_of_reclassifying_title(monkeypatch):
    from ai_career_navigator.market import jsearch_service

    original = jsearch_service._primary_evidence

    def with_validated_classification(*args, **kwargs):
        item = original(*args, **kwargs)
        return item.model_copy(update={"title_classification": "RELATED_TITLE"})

    monkeypatch.setattr(jsearch_service, "_primary_evidence", with_validated_classification)

    def handler(request):
        return httpx.Response(200, json={"status": "OK", "data": [raw()]})

    result = asyncio.run(retrieve_jsearch_market(goal(), client(handler), now=NOW))
    assert result.posting_audits[0].title_classification == "RELATED_TITLE"
    assert result.posting_evidence[0].title_classification == "RELATED_TITLE"
    assert result.snapshot.related_title_count == result.related_title_validated_count == 1
    assert result.snapshot.exact_title_count == result.exact_title_validated_count == 0


def test_runtime_does_not_construct_either_legacy_client():
    from ai_career_navigator.market.schemas import SearchLimits
    from ai_career_navigator.orchestration.context import (
        TransientMarketContentStore,
        WorkflowRuntimeContext,
    )

    def forbidden():
        raise AssertionError("Legacy provider must not be constructed")

    def handler(request):
        unrelated = raw("unrelated", "Prepare meals.") | {"job_title": "Executive Chef"}
        return httpx.Response(200, json={"status": "OK", "data": [raw(), unrelated]})

    context = WorkflowRuntimeContext(
        settings=Settings(_env_file=None),
        model_gateway=None,
        market_client_factory=forbidden,
        structured_market_client_factory=lambda: client(handler),
        content_store=TransientMarketContentStore(),
    )
    result = asyncio.run(context.retrieve_market(goal(), limits=SearchLimits(), now=NOW))
    assert result.primary_provider == "JSEARCH"
    assert len(result.posting_evidence) == 1
    assert result.raw_source_count == len(result.posting_audits) == 2
    from uuid import uuid4

    run_id = uuid4()
    context.content_store.put_posting_evidence(run_id, result.posting_evidence)
    inputs = context.content_store.get_processing_inputs(run_id)
    assert len(inputs) == 1
    assert inputs[0].posting.original_title == "AI Solutions Architect"


def test_search_v2_contract_handles_nulls_and_alternative_application_links():
    job = raw() | {
        "job_uid": "secondary-id",
        "job_publisher": "Employer careers",
        "job_apply_link": None,
        "apply_options": [
            None,
            {"apply_link": "javascript:bad"},
            {"apply_link": "https://example.org/jobs/1"},
            {"apply_link": "https://other.example.org/jobs/1"},
        ],
        "job_highlights": {},
        "job_min_salary": None,
        "job_benefits": None,
        "job_employment_type": None,
        "job_is_remote": False,
        "job_posted_at_datetime_utc": None,
        "job_location": "Toronto, ON, Canada",
    }
    page = normalize_jsearch_payload(
        {
            "status": "OK",
            "request_id": "test-request",
            "data": {"jobs": [job], "cursor": "opaque-must-not-be-stored"},
        }
    )
    assert len(page.results) == page.input_result_count == 1
    assert page.continuation_available
    assert page.response_request_id == "test-request"
    assert "opaque-must-not-be-stored" not in page.model_dump_json()
    item = page.results[0]
    assert item.provider_job_id == "1"
    assert item.provider_stable_id == "secondary-id"
    assert item.description == raw()["job_description"]
    assert item.created is None
    assert item.description_origin == "SEARCH_DESCRIPTION"
    assert item.is_remote is False


def test_display_location_is_not_masked_by_country_when_city_state_absent():
    job = raw() | {"job_city": None, "job_state": None, "job_location": "Markham, ON, Canada"}
    page = normalize_jsearch_payload({"status": "OK", "data": [job]})
    assert page.results[0].location == "Markham, ON, Canada"


def test_highlights_are_limited_fallback_not_benefits_or_salary():
    job = raw(description="") | {
        "job_highlights": {
            "Responsibilities": ["Design AI services", None],
            "Qualifications": ["Python experience required"],
            "Benefits": ["Free lunch"],
        },
        "job_min_salary": 100000,
    }

    def handler(request):
        return httpx.Response(200, json={"status": "OK", "data": [job]})

    result = asyncio.run(retrieve_jsearch_market(goal(), client(handler, max_details=0), now=NOW))
    item = result.posting_evidence[0]
    assert (
        item.primary_content.markdown
        == "Responsibilities\nDesign AI services\n\nQualifications\nPython experience required"
    )
    assert "lunch" not in item.primary_content.markdown
    audit = result.posting_audits[0]
    assert audit.routing_decision == "RETAINED_LIMITED_CONTENT"
    assert audit.enrichment_status == "NOT_ATTEMPTED"
    assert "not attempted" in " ".join(audit.routing_notes)
    assert result.enrichment_attempt_count == 0


def test_highlights_trigger_details_with_full_job_id_not_uid():
    full_id = "opaque-long-job-id=="
    job = raw(full_id, "") | {
        "job_uid": "short-id",
        "job_highlights": {"Qualifications": ["Python experience required " * 10]},
    }
    calls = []

    def handler(request):
        calls.append(request)
        if request.url.path == "/search-v2":
            return httpx.Response(200, json={"status": "OK", "data": {"jobs": [job]}})
        assert request.url.params["job_id"] == full_id
        return httpx.Response(200, json={"status": "OK", "data": [raw(full_id)]})

    result = asyncio.run(retrieve_jsearch_market(goal(), client(handler), now=NOW))
    assert len(calls) == 2
    assert result.enrichment_success_count == 1
    assert result.posting_evidence[0].primary_content.markdown == raw()["job_description"]
    assert result.posting_audits[0].enrichment_observation["description_origin"] == "JOB_DETAILS"
    assert result.posting_audits[0].routing_decision == "RETAINED_DESCRIPTION"


def test_raw_counts_include_malformed_records_without_storing_raw_payload():
    def handler(request):
        return httpx.Response(
            200,
            json={
                "status": "OK",
                "request_id": "trace-id",
                "data": {"jobs": [raw(), None, {"job_title": "bad"}], "cursor": "never-follow"},
            },
        )

    result = asyncio.run(retrieve_jsearch_market(goal(), client(handler), now=NOW))
    assert result.raw_source_count == 3
    assert result.total_unique_retained_posting_count == 1
    assert result.rejected_result_count == 2
    assert len(result.normalization_issues) == 2
    assert result.continuation_available
    assert result.provider_request_id == "trace-id"
    assert "never-follow" not in result.model_dump_json()


def test_records_over_normalization_bound_are_deferred_not_lost_or_rejected():
    jobs = [raw(str(index)) for index in range(52)]
    page = normalize_jsearch_payload({"status": "OK", "data": {"jobs": jobs}})
    assert page.input_result_count == 52
    assert len(page.results) == 50
    assert page.deferred_result_count == 2
    assert page.malformed_result_count == 0


def test_short_complete_description_is_not_forced_into_details():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            200, json={"status": "OK", "data": [raw(description="Python required.")]}
        )

    result = asyncio.run(retrieve_jsearch_market(goal(), client(handler), now=NOW))
    assert len(calls) == 1
    assert result.posting_audits[0].routing_decision == "RETAINED_DESCRIPTION"
    assert result.posting_evidence[0].primary_content.content_complete is None


def test_details_highlights_do_not_become_a_full_description():
    def handler(request):
        job = raw(description="")
        if request.url.path == "/job-details":
            job["job_highlights"] = {"Qualifications": ["Python experience required."]}
        return httpx.Response(200, json={"status": "OK", "data": [job]})

    result = asyncio.run(retrieve_jsearch_market(goal(), client(handler), now=NOW))
    assert result.enrichment_success_count == 1
    assert result.posting_audits[0].routing_decision == "RETAINED_LIMITED_CONTENT"
    assert (
        result.posting_audits[0].enrichment_observation["description_origin"]
        == "JOB_DETAILS_HIGHLIGHTS"
    )
    assert result.posting_evidence[0].primary_content.content_complete is False


def test_search_wait_budget_is_independent_of_shorter_details_timeout():
    from ai_career_navigator.market.schemas import StructuredJobSearchRequest

    requests = []

    def handler(request):
        requests.append(request)
        budget = request.extensions["timeout"]
        assert budget["connect"] == budget["write"] == budget["pool"] == 10
        assert budget["read"] == (90 if request.url.path == "/search-v2" else 30)
        return httpx.Response(200, json={"status": "OK", "data": [raw()]})

    async def run():
        async with client(handler) as api:
            await api.search_page(StructuredJobSearchRequest(title="Developer", location="Toronto"))
            await api.job_details("1", country="ca")

    asyncio.run(run())
    assert len(requests) == 2


def test_slow_response_between_old_and_new_budget_is_accepted():
    from ai_career_navigator.market.schemas import StructuredJobSearchRequest

    def handler(request):
        # Deterministic transport simulation: a 45s upstream wait exceeds old 30s budget.
        if request.extensions["timeout"]["read"] < 45:
            raise httpx.ReadTimeout("private response details")
        return httpx.Response(200, json={"status": "OK", "data": [raw()]})

    async def run():
        async with client(handler) as api:
            return await api.search_page(
                StructuredJobSearchRequest(title="Developer", location="Toronto")
            )

    assert len(asyncio.run(run()).results) == 1


def test_timeout_has_safe_phase_diagnostic_and_no_retry(caplog):
    from ai_career_navigator.market.errors import MarketTimeoutError

    requests = []

    def handler(request):
        requests.append(request)
        raise httpx.ReadTimeout("private-test-token private query content")

    with pytest.raises(MarketTimeoutError):
        asyncio.run(retrieve_jsearch_market(goal(), client(handler), now=NOW))
    assert len(requests) == 1
    assert "phase=ReadTimeout" in caplog.text
    assert "read_budget_seconds=90" in caplog.text
    assert "private-test-token" not in caplog.text
    assert "private query content" not in caplog.text


def test_settings_apply_separate_search_timeout_without_changing_legacy_budget():
    settings = Settings(_env_file=None, rapidapi_key="test-key", market_timeout_seconds=30)
    api = JSearchMarketClient.from_settings(settings)
    assert api._search_timeout == 90
    assert api._timeout == 30


def test_total_deadline_stops_slow_transport_without_retry(monkeypatch):
    from ai_career_navigator.market.errors import MarketTimeoutError

    real_timeout = asyncio.timeout
    deadlines = []
    calls = []

    def short_deadline(seconds):
        deadlines.append(seconds)
        return real_timeout(0.001)

    async def handler(request):
        calls.append(request)
        await asyncio.sleep(0.05)
        return httpx.Response(200, json={"status": "OK", "data": []})

    monkeypatch.setattr(asyncio, "timeout", short_deadline)
    with pytest.raises(MarketTimeoutError):
        asyncio.run(retrieve_jsearch_market(goal(), client(handler), now=NOW))
    assert deadlines == [100]
    assert len(calls) == 1
