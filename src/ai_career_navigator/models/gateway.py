"""Provider-independent model routing, retry, validation, and safe logging."""

import json
import logging
import time
from collections.abc import Callable, Mapping
from typing import Any, TypeVar
from uuid import uuid4

from pydantic import BaseModel, ValidationError

from ai_career_navigator.config import Settings
from ai_career_navigator.models.enums import ModelRole
from ai_career_navigator.models.errors import (
    ModelAuthenticationError,
    ModelConfigurationError,
    ModelGatewayError,
    ModelResponseValidationError,
)
from ai_career_navigator.models.inspection import LocalModelInspector
from ai_career_navigator.models.protocols import ModelProvider
from ai_career_navigator.models.schemas import MetadataValue, ModelRequest, ModelResponse

StructuredModel = TypeVar("StructuredModel", bound=BaseModel)
logger = logging.getLogger(__name__)


def _schema_nodes(nodes: list[dict[str, Any]], root: dict[str, Any]) -> list[dict[str, Any]]:
    """Resolve local schema alternatives without retaining any response data."""
    pending = list(nodes)
    expanded = []
    visited_refs = set()
    while pending:
        node = pending.pop()
        reference = node.get("$ref")
        if isinstance(reference, str) and reference.startswith("#/"):
            if reference in visited_refs:
                continue
            visited_refs.add(reference)
            resolved: Any = root
            for part in reference[2:].split("/"):
                resolved = (
                    resolved.get(part.replace("~1", "/").replace("~0", "~"))
                    if isinstance(resolved, dict)
                    else None
                )
            if isinstance(resolved, dict):
                pending.append(resolved)
        expanded.append(node)
        for keyword in ("anyOf", "oneOf", "allOf"):
            pending.extend(item for item in node.get(keyword, []) if isinstance(item, dict))
    return expanded


def _safe_validation_location(location: tuple, schema: dict[str, Any]) -> str:
    """Keep schema fields/array indices; model-controlled object keys are private."""
    nodes = [schema]
    safe_parts = []
    for part in location:
        candidates = _schema_nodes(nodes, schema)
        next_nodes = []
        approved = False
        for node in candidates:
            properties = node.get("properties", {})
            if isinstance(part, str) and part in properties:
                approved = True
                if isinstance(properties[part], dict):
                    next_nodes.append(properties[part])
            elif isinstance(part, int) and node.get("type") == "array":
                approved = True
                prefix = node.get("prefixItems", [])
                child = prefix[part] if 0 <= part < len(prefix) else node.get("items")
                if isinstance(child, dict):
                    next_nodes.append(child)
        if not approved:
            # Map keys remain redacted even if they happen to equal a field name
            # elsewhere. Its value schema can still explain nested known fields.
            next_nodes = [
                child
                for node in candidates
                if isinstance((child := node.get("additionalProperties")), dict)
            ]
        safe_parts.append(str(part) if approved else "<unexpected-field>")
        nodes = next_nodes
    return ".".join(safe_parts) or "<root>"


class ModelGateway:
    """Route logical roles through one normalized provider boundary."""

    def __init__(
        self,
        *,
        provider: ModelProvider,
        models: Mapping[ModelRole, str | None],
        timeout_seconds: float,
        max_retries: int,
        sleeper: Callable[[float], None] = time.sleep,
        retry_delay_seconds: float = 0.25,
        inspector: LocalModelInspector | None = None,
        max_output_tokens: int | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ModelConfigurationError("model timeout must be greater than zero")
        if max_retries < 0:
            raise ModelConfigurationError("maximum retries cannot be negative")
        if retry_delay_seconds < 0:
            raise ModelConfigurationError("retry delay cannot be negative")
        self._provider = provider
        self._models = dict(models)
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._sleeper = sleeper
        self._retry_delay_seconds = retry_delay_seconds
        self.inspector = inspector
        if max_output_tokens is not None and max_output_tokens <= 0:
            raise ModelConfigurationError("output token override must be positive")
        self._max_output_tokens = max_output_tokens

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        providers: Mapping[str, ModelProvider] | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> "ModelGateway":
        """Create a gateway using only configuration and registered adapters."""

        from ai_career_navigator.models.providers import configured_provider

        provider = configured_provider(settings, providers)
        return cls(
            provider=provider,
            models={
                ModelRole.EXTRACTION: settings.extraction_model,
                ModelRole.REASONING: settings.reasoning_model,
                ModelRole.VALIDATION: settings.validation_model or settings.reasoning_model,
            },
            timeout_seconds=settings.model_timeout_seconds,
            max_retries=settings.max_retries,
            max_output_tokens=settings.model_max_output_tokens,
            sleeper=sleeper,
            inspector=(
                LocalModelInspector(
                    secrets=tuple(
                        value.get_secret_value()
                        for name in type(settings).model_fields
                        if hasattr((value := getattr(settings, name)), "get_secret_value")
                    )
                )
                if settings.model_inspector_enabled
                else None
            ),
        )

    def generate_text(
        self,
        *,
        role: ModelRole,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        metadata: dict[str, MetadataValue] | None = None,
    ) -> ModelResponse:
        """Generate text using the model configured for the requested logical role."""

        request = ModelRequest(
            role=role,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            metadata=metadata or {},
        )
        return self._execute(request=request)

    def generate_structured(
        self,
        *,
        role: ModelRole,
        output_schema: type[StructuredModel],
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        metadata: dict[str, MetadataValue] | None = None,
        validation_context: dict[str, Any] | None = None,
        max_retries: int | None = None,
    ) -> ModelResponse:
        """Generate and strictly validate JSON against the supplied Pydantic model."""

        request = ModelRequest(
            role=role,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            response_schema_name=output_schema.__name__,
            metadata=metadata or {},
        )
        return self._execute(
            request=request,
            output_schema=output_schema,
            validation_context=validation_context,
            max_retries=max_retries,
        )

    def _execute(
        self,
        *,
        request: ModelRequest,
        output_schema: type[StructuredModel] | None = None,
        validation_context: dict[str, Any] | None = None,
        max_retries: int | None = None,
    ) -> ModelResponse:
        if max_retries is not None and (max_retries < 0 or max_retries > self._max_retries):
            raise ModelConfigurationError("per-call retries may only reduce the configured limit")
        retry_limit = self._max_retries if max_retries is None else max_retries
        model = self._model_for(request.role)
        if self._max_output_tokens is not None:
            request = request.model_copy(update={"max_tokens": self._max_output_tokens})
        retry_count = 0
        validation_retry_used = False
        call_id = str(uuid4())

        while True:
            if self.inspector is not None:
                self.inspector.request(
                    request,
                    call_id=call_id,
                    provider=self._provider.provider_name,
                    model=model,
                    schema=output_schema.model_json_schema() if output_schema else None,
                    timeout_seconds=self._timeout_seconds,
                    max_retries=retry_limit,
                    attempt=retry_count + 1,
                )
            try:
                if output_schema is None:
                    response = self._provider.generate_text(
                        request=request,
                        model=model,
                        timeout_seconds=self._timeout_seconds,
                    )
                else:
                    response = self._provider.generate_structured(
                        request=request,
                        model=model,
                        output_schema=output_schema.model_json_schema(),
                        timeout_seconds=self._timeout_seconds,
                    )
                self._validate_routing(response, request=request, expected_model=model)
                if output_schema is not None:
                    response = self._validated_response(
                        response, output_schema, validation_context=validation_context
                    )
            except ModelResponseValidationError as error:
                self._inspect_failure(call_id, retry_count, error)
                if validation_retry_used or retry_count >= retry_limit:
                    self._log_failure(request, model, retry_count, error)
                    raise
                validation_retry_used = True
                retry_count += 1
                request = self._structured_repair_request(request, error)
                self._wait_before_retry(retry_count)
                continue
            except ModelAuthenticationError as error:
                self._inspect_failure(call_id, retry_count, error)
                self._log_failure(request, model, retry_count, error)
                raise
            except ModelGatewayError as error:
                self._inspect_failure(call_id, retry_count, error)
                if not error.retryable or retry_count >= retry_limit:
                    self._log_failure(request, model, retry_count, error)
                    raise
                retry_count += 1
                self._wait_before_retry(retry_count)
                continue
            except Exception as error:
                wrapped = ModelGatewayError("model provider adapter failed unexpectedly")
                self._inspect_failure(call_id, retry_count, wrapped)
                self._log_failure(request, model, retry_count, wrapped)
                raise wrapped from error

            if self.inspector is not None:
                self.inspector.record(
                    "validated_response",
                    call_id=call_id,
                    attempt=retry_count + 1,
                    structured_output=response.structured_output,
                    finish_reason=response.finish_reason,
                    latency_ms=response.latency_ms,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    validation="SCHEMA_VALIDATED" if output_schema else "TEXT_NOT_RETAINED",
                )
            logger.info(
                "model_call_succeeded provider=%s model=%s role=%s latency_ms=%.2f "
                "retry_count=%d input_tokens=%s output_tokens=%s",
                response.provider,
                response.model,
                response.role.value,
                response.latency_ms,
                retry_count,
                response.input_tokens,
                response.output_tokens,
            )
            return response

    def _inspect_failure(self, call_id: str, retry_count: int, error: ModelGatewayError) -> None:
        if self.inspector is not None:
            self.inspector.record(
                "rejected_response",
                call_id=call_id,
                attempt=retry_count + 1,
                failure_category=type(error).__name__,
                validation_issue=str(error)[:500]
                if isinstance(error, ModelResponseValidationError)
                else None,
            )

    def _model_for(self, role: ModelRole) -> str:
        model = self._models.get(role)
        if not model:
            raise ModelConfigurationError(f"no model configured for role {role.value}")
        return model

    @staticmethod
    def _validate_routing(
        response: ModelResponse, *, request: ModelRequest, expected_model: str
    ) -> None:
        if response.role is not request.role or response.model != expected_model:
            raise ModelGatewayError("provider returned inconsistent routing metadata")

    @staticmethod
    def _validated_response(
        response: ModelResponse,
        output_schema: type[StructuredModel],
        *,
        validation_context: dict[str, Any] | None = None,
    ) -> ModelResponse:
        if response.finish_reason == "length":
            raise ModelResponseValidationError(
                f"model output failed validation for {output_schema.__name__}: truncated_response"
            )
        try:
            candidate: Any = response.structured_output
            if candidate is None:
                candidate = json.loads(response.content)
        except json.JSONDecodeError as error:
            raise ModelResponseValidationError(
                f"model output failed validation for {output_schema.__name__}: invalid_json"
            ) from error
        except TypeError as error:
            raise ModelResponseValidationError(
                f"model output failed validation for {output_schema.__name__}: invalid_structure"
            ) from error
        try:
            validated = output_schema.model_validate(candidate, context=validation_context)
        except ValidationError as error:
            schema = output_schema.model_json_schema()
            safe_details = ", ".join(
                f"{_safe_validation_location(item['loc'], schema)}:{item['type']}"
                for item in error.errors(
                    include_url=False, include_context=False, include_input=False
                )
            )[:500]
            raise ModelResponseValidationError(
                f"model output failed validation for {output_schema.__name__}: {safe_details}"
            ) from None
        return response.model_copy(update={"structured_output": validated.model_dump(mode="json")})

    @staticmethod
    def _structured_repair_request(
        request: ModelRequest, error: ModelResponseValidationError
    ) -> ModelRequest:
        """Create one schema-only correction request without echoing rejected output."""

        repair = (
            "\n\nThe previous response was rejected by strict schema validation. "
            f"Sanitized issue: {str(error)[:500]}. "
            "Return a complete replacement JSON object matching the supplied schema exactly."
        )
        return request.model_copy(
            update={
                "system_prompt": f"{request.system_prompt}{repair}",
                "metadata": {**request.metadata, "structured_retry": True},
            }
        )

    def _wait_before_retry(self, retry_count: int) -> None:
        delay = min(self._retry_delay_seconds * (2 ** (retry_count - 1)), 2.0)
        self._sleeper(delay)

    def _log_failure(
        self, request: ModelRequest, model: str, retry_count: int, error: ModelGatewayError
    ) -> None:
        validation_issue = (
            str(error)[:500] if isinstance(error, ModelResponseValidationError) else None
        )
        logger.warning(
            "model_call_failed provider=%s model=%s role=%s retry_count=%d category=%s "
            "validation_issue=%s",
            self._provider.provider_name,
            model,
            request.role.value,
            retry_count,
            type(error).__name__,
            validation_issue,
        )
