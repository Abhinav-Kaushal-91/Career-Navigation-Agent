import pytest
from pydantic import BaseModel

from ai_career_navigator.models import (
    ModelGateway,
    ModelResponseValidationError,
    ModelRole,
    ModelTimeoutError,
)
from ai_career_navigator.models.providers import FakeModelProvider


class ExtractedPerson(BaseModel):
    name: str
    years_experience: int


def gateway(provider: FakeModelProvider, *, max_retries: int = 1) -> ModelGateway:
    return ModelGateway(
        provider=provider,
        models={ModelRole.EXTRACTION: "extract-model"},
        timeout_seconds=10,
        max_retries=max_retries,
        sleeper=lambda _: None,
    )


def test_structured_output_is_validated_and_normalized() -> None:
    provider = FakeModelProvider(outcomes=['{"name":"Ada","years_experience":8}'])

    response = gateway(provider).generate_structured(
        role=ModelRole.EXTRACTION,
        output_schema=ExtractedPerson,
        system_prompt="Return JSON",
        user_prompt="Extract profile",
    )

    assert response.structured_output == {"name": "Ada", "years_experience": 8}
    assert provider.calls[0].output_schema == ExtractedPerson.model_json_schema()


def test_malformed_json_gets_at_most_one_controlled_retry() -> None:
    provider = FakeModelProvider(outcomes=["not-json", "still-not-json", "unused"])

    with pytest.raises(ModelResponseValidationError):
        gateway(provider, max_retries=4).generate_structured(
            role=ModelRole.EXTRACTION,
            output_schema=ExtractedPerson,
            system_prompt="Return JSON",
            user_prompt="Extract profile",
        )

    assert len(provider.calls) == 2


def test_invalid_structured_response_is_repaired_once() -> None:
    malformed = '{"name":"Ada"}'
    provider = FakeModelProvider(outcomes=[malformed, '{"name":"Ada","years_experience":8}'])

    response = gateway(provider).generate_structured(
        role=ModelRole.EXTRACTION,
        output_schema=ExtractedPerson,
        system_prompt="Return JSON",
        user_prompt="Extract profile",
    )

    assert response.structured_output == {"name": "Ada", "years_experience": 8}
    assert len(provider.calls) == 2
    retry = provider.calls[1].request
    assert retry.metadata["structured_retry"] is True
    assert "years_experience:missing" in retry.system_prompt
    assert malformed not in retry.system_prompt


def test_transient_structured_timeout_is_retried_once() -> None:
    provider = FakeModelProvider(
        outcomes=[ModelTimeoutError("timeout"), '{"name":"Ada","years_experience":8}']
    )

    response = gateway(provider).generate_structured(
        role=ModelRole.EXTRACTION,
        output_schema=ExtractedPerson,
        system_prompt="Return JSON",
        user_prompt="Extract profile",
    )

    assert response.structured_output == {"name": "Ada", "years_experience": 8}
    assert len(provider.calls) == 2


def test_repeated_structured_timeout_fails_safely() -> None:
    provider = FakeModelProvider(outcomes=[ModelTimeoutError("first"), ModelTimeoutError("second")])

    with pytest.raises(ModelTimeoutError):
        gateway(provider).generate_structured(
            role=ModelRole.EXTRACTION,
            output_schema=ExtractedPerson,
            system_prompt="Return JSON",
            user_prompt="Extract profile",
        )

    assert len(provider.calls) == 2


def test_schema_mismatch_is_never_silently_accepted() -> None:
    provider = FakeModelProvider(outcomes=['{"name":"Ada"}'])

    with pytest.raises(ModelResponseValidationError, match="ExtractedPerson"):
        gateway(provider, max_retries=0).generate_structured(
            role=ModelRole.EXTRACTION,
            output_schema=ExtractedPerson,
            system_prompt="Return JSON",
            user_prompt="Extract profile",
        )
