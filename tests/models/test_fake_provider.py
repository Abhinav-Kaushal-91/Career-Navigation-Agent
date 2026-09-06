import pytest

from ai_career_navigator.models import ModelRole, ModelTimeoutError
from ai_career_navigator.models.providers import FakeModelProvider
from ai_career_navigator.models.schemas import ModelRequest


def request(role: ModelRole = ModelRole.EXTRACTION) -> ModelRequest:
    return ModelRequest(role=role, system_prompt="System", user_prompt="User")


def test_fake_provider_returns_deterministic_normalized_response() -> None:
    provider = FakeModelProvider(outcomes=["first response"])

    first = provider.generate_text(request=request(), model="extract-model", timeout_seconds=10)
    second = provider.generate_text(request=request(), model="extract-model", timeout_seconds=10)

    assert first.content == "first response"
    assert second.content == "Deterministic fake response"
    assert first.provider == "mock"
    assert first.request_id == "fake-1"
    assert len(provider.calls) == 2


def test_fake_provider_records_structured_schema() -> None:
    provider = FakeModelProvider(outcomes=['{"name":"Ada"}'])
    schema = {"type": "object", "properties": {"name": {"type": "string"}}}

    provider.generate_structured(
        request=request(), model="extract-model", output_schema=schema, timeout_seconds=10
    )

    assert provider.calls[0].structured
    assert provider.calls[0].output_schema == schema


def test_fake_provider_can_simulate_typed_failure() -> None:
    provider = FakeModelProvider(outcomes=[ModelTimeoutError("simulated timeout")])

    with pytest.raises(ModelTimeoutError, match="simulated timeout"):
        provider.generate_text(request=request(), model="extract-model", timeout_seconds=10)
