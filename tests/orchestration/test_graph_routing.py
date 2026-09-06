import asyncio

from ai_career_navigator.domain import ApprovalStatus, CareerGoal, GoalType
from ai_career_navigator.market import MarketAuthenticationError
from ai_career_navigator.market.mcp.fake_client import FakeMarketSearchClient
from ai_career_navigator.models import ModelTimeoutError
from ai_career_navigator.models.providers import FakeModelProvider
from ai_career_navigator.orchestration import (
    CapabilityWorkflowStatus,
    MarketSearchWorkflowStatus,
    WorkflowStatus,
)

from .conftest import NOW, empty_inference_json, make_controller


def test_stream_start_reports_only_nodes_that_really_completed() -> None:
    controller, _ = make_controller(FakeModelProvider())

    async def collect() -> list[str]:
        return [node async for node in controller.stream_start(thread_id="stream-no-profile")]

    nodes = asyncio.run(collect())
    result = controller.inspect(thread_id="stream-no-profile")

    assert nodes == ["initialize_run", "profile_ready"]
    assert result.state["workflow_status"] is WorkflowStatus.READY_FOR_PROFILE


def test_no_profile_returns_control_without_external_calls() -> None:
    provider = FakeModelProvider()
    market = FakeMarketSearchClient()
    controller, _ = make_controller(provider, market)

    result = asyncio.run(controller.start(thread_id="missing-profile"))

    assert result.state["workflow_status"] is WorkflowStatus.READY_FOR_PROFILE
    assert provider.calls == []
    assert market.search_calls == []


def test_unapproved_profile_does_not_reach_market(approved_profile) -> None:
    profile = approved_profile.model_copy(update={"approval_status": ApprovalStatus.DRAFT})
    market = FakeMarketSearchClient()
    controller, _ = make_controller(FakeModelProvider(), market)

    result = asyncio.run(controller.start(thread_id="draft-profile", confirmed_profile=profile))

    assert result.state["workflow_status"] is WorkflowStatus.FAILED
    assert result.state["last_error"] == "INVALID_CONFIRMED_PROFILE"
    assert market.search_calls == []


def test_no_goal_returns_control_after_empty_inference(approved_profile) -> None:
    provider = FakeModelProvider(outcomes=[empty_inference_json()])
    controller, _ = make_controller(provider)

    result = asyncio.run(
        controller.start(thread_id="missing-goal", confirmed_profile=approved_profile)
    )

    assert result.state["workflow_status"] is WorkflowStatus.READY_FOR_GOAL
    assert result.state["capability_inference_status"] is CapabilityWorkflowStatus.EMPTY


def test_open_goal_requires_role_discovery_without_market_call(approved_profile) -> None:
    goal = CareerGoal(
        goal_type=GoalType.CAREER_EXPLORATION,
        target_role=None,
        target_location="Toronto, Canada",
        approval_status=ApprovalStatus.APPROVED,
        created_at=NOW,
        approved_at=NOW,
    )
    market = FakeMarketSearchClient()
    controller, _ = make_controller(FakeModelProvider(), market)

    result = asyncio.run(
        controller.start(
            thread_id="role-discovery",
            confirmed_profile=approved_profile,
            confirmed_goal=goal,
            capability_inference_requested=False,
        )
    )

    assert result.state["workflow_status"] is WorkflowStatus.ROLE_DISCOVERY_REQUIRED
    assert (
        result.state["market_search_status"] is MarketSearchWorkflowStatus.ROLE_DISCOVERY_REQUIRED
    )
    assert market.search_calls == []


def test_inference_provider_failure_degrades_to_goal_input(approved_profile) -> None:
    provider = FakeModelProvider(outcomes=[ModelTimeoutError("simulated")])
    controller, _ = make_controller(provider)

    result = asyncio.run(
        controller.start(thread_id="inference-failure", confirmed_profile=approved_profile)
    )

    assert result.state["workflow_status"] is WorkflowStatus.READY_FOR_GOAL
    assert result.state["capability_inference_status"] is CapabilityWorkflowStatus.FAILED_CONTINUED
    assert result.state["degraded_mode"]
    assert result.state["limitations"]


def test_non_retryable_market_authentication_failure_is_safe(
    approved_profile, approved_goal
) -> None:
    market = FakeMarketSearchClient(
        search_outcomes=[MarketAuthenticationError("secret provider detail")]
    )
    controller, _ = make_controller(FakeModelProvider(), market)

    result = asyncio.run(
        controller.start(
            thread_id="market-auth",
            confirmed_profile=approved_profile,
            confirmed_goal=approved_goal,
            capability_inference_requested=False,
        )
    )

    assert result.state["workflow_status"] is WorkflowStatus.FAILED
    assert result.state["last_error"] == "AUTHENTICATION_ERROR"
    assert "secret provider detail" not in str(result.state)
