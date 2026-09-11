"""Fireworks adapter using its documented OpenAI-compatible HTTP endpoint."""

import json
import subprocess
import sys
import time
from collections.abc import Callable
from http.client import HTTPResponse
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import SecretStr

from ai_career_navigator.models.errors import (
    ModelAuthenticationError,
    ModelConfigurationError,
    ModelGatewayError,
    ModelProviderError,
    ModelRateLimitError,
    ModelTimeoutError,
    ModelUnavailableError,
)
from ai_career_navigator.models.providers.base import BaseModelProvider
from ai_career_navigator.models.schemas import ModelRequest, ModelResponse

FIREWORKS_CHAT_COMPLETIONS_URL = "https://api.fireworks.ai/inference/v1/chat/completions"
HttpPost = Callable[[str, dict[str, str], bytes, float], bytes]


def _standard_http_post(url: str, headers: dict[str, str], body: bytes, timeout: float) -> bytes:
    request = Request(url, data=body, headers=headers, method="POST")
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed HTTPS provider URL
        typed_response: HTTPResponse = response
        return typed_response.read()


class FireworksProvider(BaseModelProvider):
    """Translate neutral requests to Fireworks and normalize its responses."""

    provider_name = "fireworks"

    def __init__(
        self,
        api_key: SecretStr | str,
        *,
        http_post: HttpPost | None = None,
        streaming: bool = False,
        reasoning_effort: str | None = None,
    ) -> None:
        secret = api_key.get_secret_value() if isinstance(api_key, SecretStr) else api_key
        if not secret:
            raise ModelConfigurationError("Fireworks API key is required")
        self._api_key = secret
        self._http_post = http_post or _standard_http_post
        self._streaming = streaming
        self._reasoning_effort = reasoning_effort

    def generate_text(
        self, *, request: ModelRequest, model: str, timeout_seconds: float
    ) -> ModelResponse:
        return self._generate(request=request, model=model, timeout_seconds=timeout_seconds)

    def generate_structured(
        self,
        *,
        request: ModelRequest,
        model: str,
        output_schema: dict[str, Any],
        timeout_seconds: float,
    ) -> ModelResponse:
        schema_name = request.response_schema_name or "structured_response"
        response_format = {
            "type": "json_schema",
            "json_schema": {"name": schema_name, "schema": output_schema},
        }
        return self._generate(
            request=request,
            model=model,
            timeout_seconds=timeout_seconds,
            response_format=response_format,
        )

    def _generate(
        self,
        *,
        request: ModelRequest,
        model: str,
        timeout_seconds: float,
        response_format: dict[str, Any] | None = None,
    ) -> ModelResponse:
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.user_prompt})
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": False,
        }
        if response_format is not None:
            payload["response_format"] = response_format
        effort = self._reasoning_effort
        if effort is None and model == "accounts/fireworks/models/glm-5p3-flash":
            # This deployment is thinking-only. Explicit high completed the saved
            # controlled batch; omission exhausted its output budget. See findings doc.
            effort = "high"
        if effort is not None:
            payload["reasoning_effort"] = effort

        if self._streaming:
            payload.update(stream=True, stream_options={"include_usage": True})
            return self._stream_response(payload, request, model, timeout_seconds)

        started = time.perf_counter()
        try:
            raw_response = self._http_post(
                FIREWORKS_CHAT_COMPLETIONS_URL,
                {
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json.dumps(payload).encode("utf-8"),
                timeout_seconds,
            )
        except HTTPError as error:
            self._raise_http_error(error.code)
        except TimeoutError as error:
            raise ModelTimeoutError("Fireworks request timed out") from error
        except URLError as error:
            if isinstance(error.reason, TimeoutError):
                raise ModelTimeoutError("Fireworks request timed out") from error
            raise ModelUnavailableError("Fireworks is temporarily unavailable") from error
        except ModelGatewayError:
            raise
        except Exception as error:
            raise ModelProviderError("Fireworks request failed") from error

        latency_ms = (time.perf_counter() - started) * 1000
        return self._normalize(
            raw_response, request=request, requested_model=model, latency_ms=latency_ms
        )

    @staticmethod
    def _raise_http_error(status_code: int) -> None:
        if status_code in {401, 403}:
            raise ModelAuthenticationError("Fireworks authentication failed")
        if status_code == 429:
            raise ModelRateLimitError("Fireworks rate limit reached")
        if status_code in {408, 504}:
            raise ModelTimeoutError("Fireworks request timed out")
        if status_code >= 500:
            raise ModelUnavailableError("Fireworks is temporarily unavailable")
        raise ModelProviderError(f"Fireworks request failed with HTTP status {status_code}")

    def _stream_response(self, payload, request, model, timeout_seconds):
        """Isolate network streaming so the parent can enforce a hard deadline."""
        started = time.perf_counter()
        process = subprocess.Popen(
            [sys.executable, "-m", "ai_career_navigator.models.providers.fireworks_stream_worker"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        try:
            output, _ = process.communicate(
                json.dumps(
                    {
                        "api_key": self._api_key,
                        "payload": payload,
                        "timeout": timeout_seconds,
                    }
                ).encode(),
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            raise ModelTimeoutError("Fireworks streaming deadline exceeded") from None
        try:
            envelope = json.loads(output)
        except (ValueError, TypeError):
            raise ModelProviderError("Fireworks stream worker returned no valid result") from None
        if "error_status" in envelope:
            self._raise_http_error(envelope["error_status"])
        if envelope.get("worker_error") == "timeout":
            raise ModelTimeoutError("Fireworks streaming request timed out")
        if envelope.get("worker_error") == "transport":
            raise ModelUnavailableError("Fireworks connection could not be established")
        if envelope.get("worker_error"):
            raise ModelProviderError("Fireworks stream did not finish safely")
        return self._normalize(
            output,
            request=request,
            requested_model=model,
            latency_ms=(time.perf_counter() - started) * 1000,
        )

    def _normalize(
        self,
        raw_response: bytes,
        *,
        request: ModelRequest,
        requested_model: str,
        latency_ms: float,
    ) -> ModelResponse:
        try:
            payload = json.loads(raw_response)
            choice = payload["choices"][0]
            content = choice["message"]["content"]
            if not isinstance(content, str):
                raise TypeError("message content is not text")
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as error:
            raise ModelProviderError("Fireworks returned an invalid response envelope") from error

        usage = payload.get("usage") or {}
        if "</think>" in content:
            content = content.rsplit("</think>", 1)[-1].strip()
        elif "<think>" in content:
            raise ModelProviderError("Fireworks returned reasoning without a final answer")
        finish_reason = choice.get("finish_reason")
        warnings = ["Response may be truncated"] if finish_reason == "length" else []
        return ModelResponse(
            content=content,
            provider=self.provider_name,
            model=str(payload.get("model") or requested_model),
            role=request.role,
            finish_reason=finish_reason,
            latency_ms=latency_ms,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            request_id=payload.get("id"),
            warnings=warnings,
        )
