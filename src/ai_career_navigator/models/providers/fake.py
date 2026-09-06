"""Deterministic provider for tests and local gateway development."""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from ai_career_navigator.models.errors import ModelGatewayError
from ai_career_navigator.models.providers.base import BaseModelProvider
from ai_career_navigator.models.schemas import ModelRequest, ModelResponse


@dataclass(frozen=True)
class FakeProviderCall:
    """One sanitized call observed by the fake provider."""

    request: ModelRequest
    model: str
    timeout_seconds: float
    structured: bool
    output_schema: dict[str, Any] | None = None


class FakeModelProvider(BaseModelProvider):
    """Return queued strings or raise queued errors without external calls."""

    provider_name = "mock"

    def __init__(
        self,
        outcomes: Iterable[str | Exception] = (),
        *,
        default_response: str = "Deterministic fake response",
    ) -> None:
        self._outcomes = list(outcomes)
        self._default_response = default_response
        self.calls: list[FakeProviderCall] = []

    def _respond(
        self,
        *,
        request: ModelRequest,
        model: str,
        timeout_seconds: float,
        structured: bool,
        output_schema: dict[str, Any] | None = None,
    ) -> ModelResponse:
        self.calls.append(
            FakeProviderCall(
                request=request,
                model=model,
                timeout_seconds=timeout_seconds,
                structured=structured,
                output_schema=output_schema,
            )
        )
        outcome = self._outcomes.pop(0) if self._outcomes else self._default_response
        if isinstance(outcome, Exception):
            raise outcome
        return ModelResponse(
            content=outcome,
            provider=self.provider_name,
            model=model,
            role=request.role,
            finish_reason="stop",
            latency_ms=0,
            input_tokens=1,
            output_tokens=1,
            request_id=f"fake-{len(self.calls)}",
        )

    def generate_text(
        self, *, request: ModelRequest, model: str, timeout_seconds: float
    ) -> ModelResponse:
        return self._respond(
            request=request, model=model, timeout_seconds=timeout_seconds, structured=False
        )

    def generate_structured(
        self,
        *,
        request: ModelRequest,
        model: str,
        output_schema: dict[str, Any],
        timeout_seconds: float,
    ) -> ModelResponse:
        return self._respond(
            request=request,
            model=model,
            timeout_seconds=timeout_seconds,
            structured=True,
            output_schema=output_schema,
        )


def raise_fake_error(error: ModelGatewayError) -> FakeModelProvider:
    """Create a fake whose next call raises a typed gateway error."""

    return FakeModelProvider(outcomes=[error])
