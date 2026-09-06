"""Public model-gateway contract."""

from ai_career_navigator.models.enums import ModelRole
from ai_career_navigator.models.errors import (
    ModelAuthenticationError,
    ModelConfigurationError,
    ModelGatewayError,
    ModelProviderError,
    ModelRateLimitError,
    ModelResponseValidationError,
    ModelTimeoutError,
    ModelUnavailableError,
)
from ai_career_navigator.models.gateway import ModelGateway
from ai_career_navigator.models.schemas import ModelRequest, ModelResponse
from ai_career_navigator.models.tracking import ModelUsage, TrackingModelProvider

__all__ = [
    "ModelAuthenticationError",
    "ModelConfigurationError",
    "ModelGateway",
    "ModelUsage",
    "TrackingModelProvider",
    "ModelGatewayError",
    "ModelProviderError",
    "ModelRateLimitError",
    "ModelRequest",
    "ModelResponse",
    "ModelResponseValidationError",
    "ModelRole",
    "ModelTimeoutError",
    "ModelUnavailableError",
]
