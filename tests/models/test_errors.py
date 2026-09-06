from ai_career_navigator.models import (
    ModelAuthenticationError,
    ModelConfigurationError,
    ModelGatewayError,
    ModelProviderError,
    ModelRateLimitError,
    ModelResponseValidationError,
    ModelTimeoutError,
    ModelUnavailableError,
)


def test_all_gateway_errors_share_one_public_base() -> None:
    error_types = (
        ModelConfigurationError,
        ModelProviderError,
        ModelTimeoutError,
        ModelRateLimitError,
        ModelAuthenticationError,
        ModelResponseValidationError,
        ModelUnavailableError,
    )

    assert all(issubclass(error_type, ModelGatewayError) for error_type in error_types)


def test_only_transient_provider_failures_are_retryable() -> None:
    assert ModelTimeoutError.retryable
    assert ModelRateLimitError.retryable
    assert ModelUnavailableError.retryable
    assert not ModelAuthenticationError.retryable
    assert not ModelConfigurationError.retryable
    assert not ModelResponseValidationError.retryable
