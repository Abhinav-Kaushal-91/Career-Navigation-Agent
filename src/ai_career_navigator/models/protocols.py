"""Structural contract implemented by model-provider adapters."""

from typing import Any, Protocol, runtime_checkable

from ai_career_navigator.models.schemas import ModelRequest, ModelResponse


@runtime_checkable
class ModelProvider(Protocol):
    """Provider adapter contract; SDK-specific objects must remain internal."""

    @property
    def provider_name(self) -> str: ...

    def generate_text(
        self, *, request: ModelRequest, model: str, timeout_seconds: float
    ) -> ModelResponse: ...

    def generate_structured(
        self,
        *,
        request: ModelRequest,
        model: str,
        output_schema: dict[str, Any],
        timeout_seconds: float,
    ) -> ModelResponse: ...
