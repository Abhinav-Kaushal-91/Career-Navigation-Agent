"""Process-local safe model-usage tracking for live UI validation."""

from dataclasses import dataclass, field
from typing import Any

from ai_career_navigator.models.protocols import ModelProvider
from ai_career_navigator.models.schemas import ModelRequest, ModelResponse


@dataclass
class ModelUsage:
    calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    failure_categories: list[str] = field(default_factory=list)


class TrackingModelProvider:
    """Track counts and normalized token usage without retaining prompts or content."""

    def __init__(self, provider: ModelProvider) -> None:
        self._provider = provider
        self.usage = ModelUsage()

    @property
    def provider_name(self) -> str:
        return self._provider.provider_name

    def _record(self, operation):  # type: ignore[no-untyped-def]
        self.usage.calls += 1
        try:
            response = operation()
        except Exception as error:
            self.usage.failed_calls += 1
            self.usage.failure_categories.append(type(error).__name__)
            raise
        self.usage.successful_calls += 1
        self.usage.input_tokens += response.input_tokens or 0
        self.usage.output_tokens += response.output_tokens or 0
        return response

    def generate_text(
        self, *, request: ModelRequest, model: str, timeout_seconds: float
    ) -> ModelResponse:
        return self._record(
            lambda: self._provider.generate_text(
                request=request, model=model, timeout_seconds=timeout_seconds
            )
        )

    def generate_structured(
        self,
        *,
        request: ModelRequest,
        model: str,
        output_schema: dict[str, Any],
        timeout_seconds: float,
    ) -> ModelResponse:
        return self._record(
            lambda: self._provider.generate_structured(
                request=request,
                model=model,
                output_schema=output_schema,
                timeout_seconds=timeout_seconds,
            )
        )
