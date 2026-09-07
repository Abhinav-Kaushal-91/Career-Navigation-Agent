"""Opt-in, bounded, process-local request inspection; never routine telemetry.

Enabling this recorder explicitly permits local retention of minimized model input.
Nothing is written or uploaded automatically. Export deliberately and delete exports
after review; they may contain career-sensitive information even after redaction.
"""

import copy
import re
from collections import deque
from typing import Any

from ai_career_navigator.models.providers.nvidia import build_nvidia_payload
from ai_career_navigator.models.schemas import ModelRequest

_FORBIDDEN_KEYS = {
    "authorization",
    "api_key",
    "app_key",
    "app_id",
    "password",
    "access_token",
    "reasoning_content",
    "chain_of_thought",
    "private_reasoning",
    "reasoning_trace",
}


class LocalModelInspector:
    """Store sanitized final-contract events only, with a fixed memory bound."""

    def __init__(self, *, secrets: tuple[str, ...] = (), max_events: int = 100) -> None:
        if max_events < 1:
            raise ValueError("max_events must be positive")
        self._secrets = tuple(value for value in secrets if value)
        self._events: deque[dict[str, Any]] = deque(maxlen=max_events)

    def _safe(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {
                self._safe(str(key)): self._safe(item)
                for key, item in value.items()
                if str(key).casefold() not in _FORBIDDEN_KEYS
            }
        if isinstance(value, (list, tuple)):
            return [self._safe(item) for item in value]
        if isinstance(value, str):
            for secret in self._secrets:
                value = value.replace(secret, "[REDACTED]")
            value = re.sub(r"(?is)<think>.*?</think>", "[PRIVATE TRACE REMOVED]", value)
            value = re.sub(
                r"(?i)(?:bearer\s+|(?:api[_-]?key|app_key|access_token)=)[^\s&\"']+",
                "[REDACTED]",
                value,
            )
            value = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[CONTACT REDACTED]", value)
            if len(value) > 200_000:
                return value[:200_000] + "[INSPECTOR CONTENT LIMIT; NOT COMPLETE]"
        return value

    def record(self, event: str, **fields: Any) -> None:
        self._events.append(self._safe({"event": event, **fields}))

    def request(
        self,
        request: ModelRequest,
        *,
        call_id: str,
        provider: str,
        model: str,
        schema: dict[str, Any] | None,
        timeout_seconds: float,
        max_retries: int,
        attempt: int,
    ) -> None:
        payload = (
            build_nvidia_payload(request, model, schema)
            if provider == "nvidia"
            else {"neutral_request": request.model_dump(mode="json"), "schema": schema}
        )
        self.record(
            "request",
            call_id=call_id,
            provider=provider,
            role=request.role.value,
            schema_name=request.response_schema_name,
            metadata=request.metadata,
            payload=payload,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            attempt=attempt,
            payload_kind="wire_body" if provider == "nvidia" else "neutral",
        )

    @property
    def events(self) -> list[dict[str, Any]]:
        return copy.deepcopy(list(self._events))
