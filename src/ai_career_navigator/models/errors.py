"""Typed failures exposed by the model gateway boundary."""


class ModelGatewayError(RuntimeError):
    """Base error for provider-independent model access."""

    retryable = False


class ModelConfigurationError(ModelGatewayError):
    """Model configuration is missing, invalid, or unsupported."""


class ModelProviderError(ModelGatewayError):
    """A provider failed without a more specific safe classification."""

    retryable = True


class ModelTimeoutError(ModelProviderError):
    """A provider call exceeded its configured timeout."""


class ModelRateLimitError(ModelProviderError):
    """A provider rejected a call because of a temporary rate limit."""


class ModelAuthenticationError(ModelProviderError):
    """Provider credentials are absent or rejected."""

    retryable = False


class ModelResponseValidationError(ModelGatewayError):
    """Structured model output failed JSON or Pydantic validation."""


class ModelUnavailableError(ModelProviderError):
    """The selected provider or model is temporarily unavailable."""
