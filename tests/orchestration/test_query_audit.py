import asyncio

from ai_career_navigator.market.mcp.fake_client import FakeMarketSearchClient
from ai_career_navigator.models.providers import FakeModelProvider
from ai_career_navigator.orchestration.state import serialize_graph_state

from .conftest import make_controller, requirement_json
from .test_end_to_end import market_fixture


def test_actual_query_passes_survive_safe_stop_checkpoint(approved_profile, approved_goal):
    hit, page = market_fixture()
    client = FakeMarketSearchClient(search_outcomes=[[hit]], content_outcomes={hit.url: page})
    controller, _ = make_controller(FakeModelProvider(outcomes=[requirement_json()]), client)
    result = asyncio.run(
        controller.start(
            thread_id="query-pass-audit",
            confirmed_profile=approved_profile,
            confirmed_goal=approved_goal,
            capability_inference_requested=False,
        )
    )
    state = serialize_graph_state(result.state)
    passes = state["market_search_passes"]
    assert passes
    assert passes[0]["provider"] == "YOU"
    assert passes[0]["query"] == client.search_requests[0].query
    assert passes[0]["request_parameters"] == client.search_requests[0].model_dump(mode="json")
    assert passes[0]["succeeded"] is True
    checkpoint = serialize_graph_state(controller.inspect(thread_id="query-pass-audit").state)
    assert checkpoint["market_search_passes"] == passes


def test_same_role_audit_preserves_jsearch_routes_without_full_description(tmp_path):
    import json
    from uuid import uuid4

    from ai_career_navigator.career.same_role import SameRoleAssessment
    from ai_career_navigator.market.schemas import MarketProviderSummary, PostingRetrievalAudit
    from ai_career_navigator.orchestration.audit import persist_same_role_audit
    from tests.career.test_same_role import reply

    assessment = SameRoleAssessment(
        **reply().model_dump(),
        profile_id=uuid4(),
        profile_version=1,
        goal_id=uuid4(),
        goal_version=1,
        posting_sources={},
        source_lines={},
        candidate_sources={},
    )
    state = {
        "run_id": uuid4(),
        "market_provider_summary": MarketProviderSummary(
            primary_provider="JSEARCH",
            raw_source_count=2,
            normalization_issues=["Result 2: expected a job object"],
            continuation_available=True,
            provider_request_id="request-id",
        ),
        "market_posting_audits": [
            PostingRetrievalAudit(
                provider="JSEARCH",
                source_type="STRUCTURED_JOB",
                title="Developer",
                source_url="https://example.org/job/1",
                routing_decision="RETAINED_LIMITED_CONTENT",
                routing_notes=["Only highlights available."],
                enrichment_status="NOT_ATTEMPTED",
                enrichment_observation={"description_origin": "SEARCH_HIGHLIGHTS"},
            )
        ],
    }
    saved = json.loads(
        persist_same_role_audit(state, assessment, None, directory=tmp_path).read_text()
    )
    assert saved["retrieval_summary"]["raw_source_count"] == 2
    assert saved["retrieval_summary"]["normalization_issues"]
    assert saved["retrieval_summary"]["continuation_available"] is True
    assert saved["retrieval_postings"][0]["routing_decision"] == "RETAINED_LIMITED_CONTENT"
    assert saved["retrieval_postings"][0]["enrichment_status"] == "NOT_ATTEMPTED"
    assert "job_description" not in saved["retrieval_postings"][0]
