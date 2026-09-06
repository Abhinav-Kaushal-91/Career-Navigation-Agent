import logging

import pytest

from ai_career_navigator.config import Settings
from ai_career_navigator.models import (
    ModelAuthenticationError,
    ModelConfigurationError,
    ModelGateway,
    ModelGatewayError,
    ModelRole,
    ModelTimeoutError,
    ModelUnavailableError,
)
from ai_career_navigator.models.providers import FakeModelProvider

MODELS = {
    ModelRole.EXTRACTION: "extract-model",
    ModelRole.REASONING: "reason-model",
    ModelRole.VALIDATION: "validate-model",
}


def gateway(provider: FakeModelProvider, *, max_retries: int = 2) -> ModelGateway:
    return ModelGateway(
        provider=provider,
        models=MODELS,
        timeout_seconds=17,
        max_retries=max_retries,
        sleeper=lambda _: None,
    )


@pytest.mark.parametrize(
    ("role", "expected_model"),
    (
        (ModelRole.EXTRACTION, "extract-model"),
        (ModelRole.REASONING, "reason-model"),
        (ModelRole.VALIDATION, "validate-model"),
    ),
)
def test_logical_role_routes_to_configured_model(role: ModelRole, expected_model: str) -> None:
    provider = FakeModelProvider()

    response = gateway(provider).generate_text(
        role=role, system_prompt="Follow instructions", user_prompt="Return a short answer"
    )

    assert response.model == expected_model
    assert response.role is role
    assert provider.calls[0].timeout_seconds == 17


def test_from_settings_selects_registered_configured_provider() -> None:
    provider = FakeModelProvider()
    settings = Settings(
        llm_provider="mock",
        extraction_model="settings-extract",
        reasoning_model="settings-reason",
        validation_model="settings-validate",
    )

    response = ModelGateway.from_settings(settings, providers={"mock": provider}).generate_text(
        role=ModelRole.REASONING,
        system_prompt="System",
        user_prompt="User",
    )

    assert response.model == "settings-reason"


def test_nvidia_provider_without_key_fails_cleanly() -> None:
    with pytest.raises(ModelConfigurationError, match="NVIDIA_API_KEY"):
        ModelGateway.from_settings(Settings(llm_provider="nvidia"))


def test_optional_validation_role_fails_only_when_requested_without_model() -> None:
    provider = FakeModelProvider()
    model_gateway = ModelGateway(
        provider=provider,
        models={
            ModelRole.EXTRACTION: "extract-model",
            ModelRole.REASONING: "reason-model",
            ModelRole.VALIDATION: None,
        },
        timeout_seconds=10,
        max_retries=0,
    )

    with pytest.raises(ModelConfigurationError, match="VALIDATION"):
        model_gateway.generate_text(
            role=ModelRole.VALIDATION, system_prompt="System", user_prompt="User"
        )

    assert provider.calls == []


def test_timeout_is_retried_when_budget_remains() -> None:
    provider = FakeModelProvider(outcomes=[ModelTimeoutError("timeout"), "recovered"])

    response = gateway(provider, max_retries=1).generate_text(
        role=ModelRole.EXTRACTION, system_prompt="System", user_prompt="User"
    )

    assert response.content == "recovered"
    assert len(provider.calls) == 2


def test_transient_retries_are_bounded() -> None:
    provider = FakeModelProvider(outcomes=[ModelUnavailableError("down") for _ in range(4)])

    with pytest.raises(ModelUnavailableError):
        gateway(provider, max_retries=2).generate_text(
            role=ModelRole.REASONING, system_prompt="System", user_prompt="User"
        )

    assert len(provider.calls) == 3


def test_authentication_error_is_not_retried() -> None:
    provider = FakeModelProvider(outcomes=[ModelAuthenticationError("bad credentials"), "unused"])

    with pytest.raises(ModelAuthenticationError):
        gateway(provider).generate_text(
            role=ModelRole.EXTRACTION, system_prompt="System", user_prompt="User"
        )

    assert len(provider.calls) == 1


def test_unexpected_provider_exception_becomes_gateway_error() -> None:
    provider = FakeModelProvider(outcomes=[ValueError("provider internals")])

    with pytest.raises(ModelGatewayError, match="adapter failed unexpectedly"):
        gateway(provider).generate_text(
            role=ModelRole.EXTRACTION, system_prompt="System", user_prompt="User"
        )


def test_safe_logs_exclude_prompts_and_secrets(caplog: pytest.LogCaptureFixture) -> None:
    secret = "fake-secret-that-must-not-appear"
    private_prompt = "private resume content"
    provider = FakeModelProvider()

    with caplog.at_level(logging.INFO):
        gateway(provider).generate_text(
            role=ModelRole.EXTRACTION,
            system_prompt="System",
            user_prompt=private_prompt,
            metadata={"run_id": "safe-run-id"},
        )

    assert private_prompt not in caplog.text
    assert secret not in caplog.text
    assert "provider=mock" in caplog.text
