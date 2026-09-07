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
