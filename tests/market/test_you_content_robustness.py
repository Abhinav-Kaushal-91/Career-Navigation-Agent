"""Offline You Contents contracts: one returned page, one grounded job body."""

import asyncio
import json
from copy import deepcopy
from types import SimpleNamespace

import pytest

from ai_career_navigator.market.errors import MarketContentError
from ai_career_navigator.market.mcp.you_client import (
    MAX_CONTENT_CHARACTERS,
    MAX_HTML_CHARACTERS,
    YouMcpMarketSearchClient,
    normalize_you_content_payload,
)

URL = "https://jobs.example.test/vacancy/123"
BODY = (
    "<h2>Responsibilities</h2><p>Develop Python services and maintain automated tests.</p>"
    "<h2>Qualifications</h2><ul><li>Python production experience.</li>"
    "<li>Experience designing HTTP APIs and working with SQL databases.</li></ul>"
)


def job(**updates):
    return {
        "@type": "JobPosting",
        "title": "Python Developer",
        "description": BODY,
        "hiringOrganization": {"@type": "Organization", "name": "Example Employer"},
        "jobLocation": {"address": {"addressLocality": "Toronto", "addressCountry": "Canada"}},
        "datePosted": "2026-09-06",
        "validThrough": "2026-10-06",
        "identifier": {"value": "REQ-123"},
        "url": URL,
        **updates,
    }


def html(records):
    return (
        "<html><head><script type='application/ld+json'>"
        + json.dumps(records)
        + "</script></head><body><nav>Browse all jobs</nav>"
        "<h1>Careers</h1><p>Unrelated site-wide marketing text.</p></body></html>"
    )


def test_html_json_ld_supplies_only_one_job_description_not_the_generic_page():
    result = normalize_you_content_payload(
        [{"url": URL, "markdown": None, "html": html({"@graph": [job()]})}], URL
    )
    assert result.title == "Python Developer"
    assert result.employer == "Example Employer"
    assert result.location == "Toronto, Canada"
    assert result.requisition_id == "REQ-123"
    assert result.posting_date == "2026-09-06"
    assert result.closing_date == "2026-10-06"
    assert result.canonical_job_url == URL
    assert result.url == URL
    assert "Python production experience." in result.markdown
    assert "Unrelated site-wide" not in result.markdown
    assert "<li>" not in result.markdown
    assert result.content_complete is True
    assert result.active_status is None


def test_metadata_json_ld_overrides_thin_markdown_with_isolated_job_body():
    record = {"url": URL, "markdown": "Apply now", "metadata": {"json_ld": [job()]}}
    original = deepcopy(record)
    result = normalize_you_content_payload({"contents": [record]}, URL)
    assert result.content_complete is True
    assert "Qualifications" in result.markdown
    assert "Apply now" not in result.markdown
    assert record == original


def test_metadata_and_html_duplicate_of_the_same_json_record_is_not_two_jobs():
    result = normalize_you_content_payload(
        {"url": URL, "html": html(job()), "metadata": {"structured_data": job()}}, URL
    )
    assert result.requisition_id == "REQ-123"


@pytest.mark.parametrize(
    "records", [lambda: [job(), job(url=URL + "4")], lambda: [job(), job(title="Nurse")]]
)
def test_multiple_distinct_jobs_are_not_implicitly_merged(records):
    with pytest.raises(MarketContentError, match="multiple distinct"):
        normalize_you_content_payload({"url": URL, "html": html(records())}, URL)


def test_exact_url_selects_its_page_without_first_unrelated_response():
    result = normalize_you_content_payload(
        {
            "data": [
                {"url": URL + "4", "markdown": "Unrelated job", "title": "Nurse"},
                {"url": URL, "markdown": "Requested job", "title": "Python Developer"},
            ]
        },
        URL,
    )
    assert result.markdown == "Requested job"
    assert result.title == "Python Developer"


def test_multiple_pages_without_requested_url_are_rejected():
    with pytest.raises(MarketContentError, match="one requested page"):
        normalize_you_content_payload(
            [{"url": URL + "4", "markdown": "Other"}, {"url": URL + "5", "text": "Other"}], URL
        )


def test_arbitrary_nested_metadata_content_is_not_a_page_response():
    with pytest.raises(MarketContentError):
        normalize_you_content_payload({"metadata": {"unrelated": {"text": "Not a page"}}}, URL)


def test_single_redirect_retains_returned_url_for_service_identity_validation():
    returned_url = "https://another.example.test/jobs/redirected"
    result = normalize_you_content_payload([{"url": returned_url, "markdown": "Page text"}], URL)
    assert result.url == returned_url
    assert result.canonical_job_url is None
    assert result.content_complete is None


def test_query_parameters_identify_different_jobs():
    first = {"url": URL + "?job=1", "markdown": "First"}
    second = {"url": URL + "?job=2", "markdown": "Second"}
    assert normalize_you_content_payload([first, second], second["url"]).markdown == "Second"


def test_failed_crawl_null_fields_are_not_a_successful_content_fetch():
    with pytest.raises(MarketContentError, match="no usable page body"):
        normalize_you_content_payload(
            {"output": [{"url": URL, "markdown": None, "html": None}]}, URL
        )


def test_whitespace_only_body_is_not_a_successful_content_fetch():
    with pytest.raises(MarketContentError, match="no usable page body"):
        normalize_you_content_payload(
            {"output": [{"url": URL, "markdown": " \n\t ", "html": "<div> </div>"}]}, URL
        )


def test_observed_mcp_output_envelope_selects_the_returned_page():
    payload = {
        "output": [
            {
                "url": URL,
                "title": "Python Developer",
                "html": "<h1>Python Developer</h1><p>Develop Python services.</p>",
                "markdown": "Python Developer\nDevelop Python services.",
                "metadata": {"site_name": "", "favicon_url": "https://example.test/icon.png"},
            }
        ]
    }
    result = normalize_you_content_payload(payload, URL)
    assert result.url == URL
    assert result.title == "Python Developer"
    assert result.markdown == "Python Developer\nDevelop Python services."
    assert result.content_complete is None


def test_nested_output_envelope_selects_exact_url_without_combining_pages():
    result = normalize_you_content_payload(
        {
            "response": {
                "output": [
                    {"url": URL + "4", "markdown": "Unrelated nursing role"},
                    {"url": URL, "markdown": "Requested Python role"},
                ]
            }
        },
        URL,
    )
    assert result.markdown == "Requested Python role"


def test_output_envelope_preserves_ambiguous_page_rejection():
    with pytest.raises(MarketContentError, match="one requested page"):
        normalize_you_content_payload(
            {
                "output": [
                    {"url": URL + "4", "markdown": "Other role"},
                    {"url": URL + "5", "markdown": "Another role"},
                ]
            },
            URL,
        )


def test_output_envelope_preserves_multiple_structured_job_rejection():
    with pytest.raises(MarketContentError, match="multiple distinct"):
        normalize_you_content_payload(
            {"output": [{"url": URL, "html": html([job(), job(url=URL + "4")])}]}, URL
        )


def test_isolated_job_locations_override_sitewide_location_and_preserve_multiple_places():
    record = job(
        jobLocation=[
            {"address": {"addressLocality": "Toronto", "addressCountry": {"name": "Canada"}}},
            {"address": {"addressLocality": "Vancouver", "addressCountry": "Canada"}},
        ]
    )
    result = normalize_you_content_payload(
        {
            "url": URL,
            "markdown": "Thin",
            "location": "Website headquarters",
            "metadata": {"json_ld": record},
        },
        URL,
    )
    assert result.location == "Toronto, Canada; Vancouver, Canada"


def test_oversized_metadata_and_invalid_returned_urls_are_rejected_not_silently_rewritten():
    with pytest.raises(MarketContentError, match="metadata exceeded"):
        normalize_you_content_payload({"url": URL, "markdown": "Text", "title": "A" * 2049}, URL)
    with pytest.raises(MarketContentError, match="invalid returned URL"):
        normalize_you_content_payload({"url": "javascript:alert(1)", "markdown": "Text"}, URL)


def test_html_without_structured_job_is_cleaned_but_not_claimed_complete():
    result = normalize_you_content_payload(
        {"url": URL, "markdown": "", "html": "<nav>Menu</nav><h1>Vacancy</h1>" + BODY}, URL
    )
    assert "Python production" in result.markdown
    assert "Menu" not in result.markdown
    assert result.content_complete is None


def test_length_alone_does_not_prove_completeness_and_truncation_is_visible():
    result = normalize_you_content_payload(
        {"url": URL, "markdown": "Career marketing. " * 4000}, URL
    )
    assert len(result.markdown) == MAX_CONTENT_CHARACTERS
    assert result.content_complete is False
    thin_job = normalize_you_content_payload(
        {
            "url": URL,
            "metadata": {"json_ld": job(description="Long promotion. " * 1200)},
            "markdown": None,
        },
        URL,
    )
    assert thin_job.content_complete is None


def test_clipped_html_never_claims_a_full_posting_even_with_early_json_ld():
    result = normalize_you_content_payload(
        {"url": URL, "html": html(job()) + " " * MAX_HTML_CHARACTERS}, URL
    )
    assert result.content_complete is False


def test_json_ld_type_array_and_separate_sections_preserve_the_same_job_fields():
    record = job(
        **{
            "@type": ["Thing", "JobPosting"],
            "description": "Individual vacancy.",
            "responsibilities": "<p>Build and operate Python services.</p>",
            "qualifications": "<p>Production Python and SQL experience.</p>",
        }
    )
    result = normalize_you_content_payload(
        {"url": URL, "metadata": {"json_ld": json.dumps(record)}, "text": "Thin"}, URL
    )
    assert "Responsibilities\nBuild and operate" in result.markdown
    assert "Qualifications\nProduction Python" in result.markdown
    assert result.content_complete is True


@pytest.mark.parametrize("supported", [True, False])
def test_fetch_requests_documented_formats_without_an_extra_call(monkeypatch, supported):
    client = YouMcpMarketSearchClient(
        endpoint="https://api.you.com/mcp", api_key="synthetic", timeout_seconds=1
    )
    client._content_supports_formats = supported
    calls = []

    async def call(tool, arguments):
        calls.append((tool, arguments))
        return [{"url": URL, "markdown": "Content"}]

    monkeypatch.setattr(client, "_call", call)
    asyncio.run(client.fetch_content(URL))
    expected = {"urls": [URL]}
    if supported:
        expected["formats"] = ["markdown", "html", "metadata"]
    assert calls == [("you-contents", expected)]


def test_discovered_format_enum_is_respected(monkeypatch):
    import ai_career_navigator.market.mcp.you_client as module

    class Context:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

    class Client(Context):
        async def list_tools(self):
            return SimpleNamespace(
                tools=[
                    SimpleNamespace(name="you-search", input_schema={"properties": {"query": {}}}),
                    SimpleNamespace(
                        name="you-contents",
                        input_schema={
                            "properties": {
                                "url": {},
                                "formats": {"items": {"enum": ["markdown", "metadata"]}},
                            }
                        },
                    ),
                ]
            )

    monkeypatch.setattr(module.httpx2, "AsyncClient", lambda **kwargs: Context())
    monkeypatch.setattr(module, "streamable_http_client", lambda *args, **kwargs: object())
    monkeypatch.setattr(module, "Client", lambda *args, **kwargs: Client())
    client = YouMcpMarketSearchClient(
        endpoint="https://api.you.com/mcp", api_key="synthetic", timeout_seconds=1
    )

    async def run():
        async with client:
            assert client._content_argument == "url"
            assert client._content_formats == ["markdown", "metadata"]

    asyncio.run(run())
