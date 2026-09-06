"""NVIDIA NIM adapter for the OpenAI-compatible chat-completions endpoint."""

import json
import time
from collections.abc import Callable
from http.client import HTTPResponse
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import SecretStr

from ai_career_navigator.models.enums import ModelRole
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

NVIDIA_NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"
NVIDIA_NIM_CHAT_COMPLETIONS_URL = f"{NVIDIA_NIM_BASE_URL}/chat/completions"
HttpPost = Callable[[str, dict[str, str], bytes, float], bytes]


def _standard_http_post(url: str, headers: dict[str, str], body: bytes, timeout: float) -> bytes:
    request = Request(url, data=body, headers=headers, method="POST")
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed HTTPS provider URL
        typed_response: HTTPResponse = response
        return typed_response.read()


class NvidiaNimProvider(BaseModelProvider):
    """Translate neutral requests to NVIDIA NIM and discard private reasoning traces."""

    provider_name = "nvidia"

    def __init__(self, api_key: SecretStr | str, *, http_post: HttpPost | None = None) -> None:
        secret = api_key.get_secret_value() if isinstance(api_key, SecretStr) else api_key
        if not secret:
            raise ModelConfigurationError("NVIDIA API key is required")
        self._api_key = secret
        self._http_post = http_post or _standard_http_post

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
        schema_instruction = (
            "Return one JSON object matching this JSON Schema exactly. "
            "Do not add keys outside the schema. Schema name: "
            f"{schema_name}. JSON Schema: "
            f"{json.dumps(output_schema, separators=(',', ':'))}"
        )
        return self._generate(
            request=request,
            model=model,
            timeout_seconds=timeout_seconds,
            response_format={"type": "json_object"},
            schema_instruction=schema_instruction,
        )

    def _generate(
        self,
        *,
        request: ModelRequest,
        model: str,
        timeout_seconds: float,
        response_format: dict[str, str] | None = None,
        schema_instruction: str | None = None,
    ) -> ModelResponse:
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        if schema_instruction:
            messages.append({"role": "system", "content": schema_instruction})
        messages.append({"role": "user", "content": request.user_prompt})

        extraction_mode = request.role in {ModelRole.EXTRACTION, ModelRole.VALIDATION}
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": 0.0 if extraction_mode else request.temperature,
            "max_tokens": request.max_tokens,
            "stream": False,
            # Nemotron can place a visible thinking trace in normal content. Keep the
            # reasoning role, but use NVIDIA's supported control to request final content only.
            "chat_template_kwargs": {"enable_thinking": False},
        }
        if response_format is not None:
            payload["response_format"] = response_format

        started = time.perf_counter()
        try:
            raw_response = self._http_post(
                NVIDIA_NIM_CHAT_COMPLETIONS_URL,
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
            raise ModelTimeoutError("NVIDIA NIM request timed out") from error
        except URLError as error:
            if isinstance(error.reason, TimeoutError):
                raise ModelTimeoutError("NVIDIA NIM request timed out") from error
            raise ModelUnavailableError("NVIDIA NIM is temporarily unavailable") from error
        except ModelGatewayError:
            raise
        except Exception as error:
            raise ModelProviderError("NVIDIA NIM request failed") from error

        latency_ms = (time.perf_counter() - started) * 1000
        return self._normalize(
            raw_response,
            request=request,
            requested_model=model,
            latency_ms=latency_ms,
        )

    @staticmethod
    def _raise_http_error(status_code: int) -> None:
        if status_code in {401, 403}:
            raise ModelAuthenticationError("NVIDIA NIM authentication failed")
        if status_code in {408, 504}:
            raise ModelTimeoutError("NVIDIA NIM request timed out")
        if status_code == 429:
            raise ModelRateLimitError("NVIDIA NIM rate limit reached")
        if status_code >= 500:
            raise ModelUnavailableError("NVIDIA NIM is temporarily unavailable")
        raise ModelProviderError(f"NVIDIA NIM request failed with HTTP status {status_code}")

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
            message = choice["message"]
            content = message["content"]
            if not isinstance(content, str):
                raise TypeError("message content is not text")
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as error:
            raise ModelProviderError("NVIDIA NIM returned an invalid response envelope") from error

        # Deliberately read only final content. Provider-specific reasoning_content is discarded.
        usage = payload.get("usage") or {}
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
