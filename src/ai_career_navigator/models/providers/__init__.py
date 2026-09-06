"""Concrete and deterministic model-provider adapters."""

from collections.abc import Mapping

from ai_career_navigator.config import Settings
from ai_career_navigator.models.errors import ModelConfigurationError
from ai_career_navigator.models.protocols import ModelProvider
from ai_career_navigator.models.providers.fake import FakeModelProvider, FakeProviderCall
from ai_career_navigator.models.providers.fireworks import FireworksProvider
from ai_career_navigator.models.providers.nvidia import NvidiaNimProvider


def configured_provider(
    settings: Settings, providers: Mapping[str, ModelProvider] | None = None
) -> ModelProvider:
    """Select the configured adapter, allowing explicit test/development overrides."""

    provider_name = settings.llm_provider.lower()
    registered = {name.lower(): provider for name, provider in (providers or {}).items()}
    if provider_name in registered:
        return registered[provider_name]
    if provider_name == "fireworks":
        if settings.fireworks_api_key is None:
            raise ModelConfigurationError(
                "FIREWORKS_API_KEY is required for LLM_PROVIDER=fireworks"
            )
        return FireworksProvider(settings.fireworks_api_key)
    if provider_name == "nvidia":
        if settings.nvidia_api_key is None:
            raise ModelConfigurationError("NVIDIA_API_KEY is required for LLM_PROVIDER=nvidia")
        return NvidiaNimProvider(settings.nvidia_api_key)
    if provider_name == "huggingface":
        raise ModelConfigurationError(f"provider adapter is not implemented: {provider_name}")
    raise ModelConfigurationError(
        f"no model provider registered for LLM_PROVIDER={settings.llm_provider}"
    )


__all__ = [
    "FakeModelProvider",
    "FakeProviderCall",
    "FireworksProvider",
    "NvidiaNimProvider",
    "configured_provider",
]
