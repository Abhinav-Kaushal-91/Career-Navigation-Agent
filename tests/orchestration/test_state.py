import asyncio
import json

from ai_career_navigator.models.providers import FakeModelProvider
from ai_career_navigator.orchestration import serialize_graph_state

from .conftest import make_controller


def test_checkpoint_state_is_json_serializable_and_excludes_runtime_objects(
    approved_profile,
) -> None:
    controller, content_store = make_controller(FakeModelProvider())
    result = asyncio.run(
        controller.start(
            thread_id="serialization",
            confirmed_profile=approved_profile,
            capability_inference_requested=False,
        )
    )

    serialized = serialize_graph_state(result.state)
    encoded = json.dumps(serialized)

    assert str(approved_profile.profile_id) in encoded
    assert "2026-09-03T16:00:00" in encoded
    assert "model_gateway" not in encoded
    assert "market_client" not in encoded
    assert "content_store" not in encoded
    assert content_store._runs == {}


def test_limitations_survive_checkpoint_and_transition(approved_profile) -> None:
    controller, _ = make_controller(FakeModelProvider())
    result = asyncio.run(
        controller.start(
            thread_id="limitations",
            confirmed_profile=approved_profile,
            capability_inference_requested=False,
        )
    )
    inspected = controller.inspect(thread_id="limitations")

    assert inspected.state["run_id"] == result.state["run_id"]
    assert inspected.state["workflow_status"] == result.state["workflow_status"]
