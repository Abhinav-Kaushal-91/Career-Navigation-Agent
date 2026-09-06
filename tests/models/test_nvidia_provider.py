import json
from typing import Any
from urllib.error import HTTPError, URLError

import pytest
from pydantic import BaseModel, ConfigDict, SecretStr

from ai_career_navigator.config import Settings
from ai_career_navigator.models import (
    ModelAuthenticationError,
    ModelGateway,
    ModelProviderError,
    ModelRateLimitError,
    ModelResponseValidationError,
    ModelRole,
    ModelTimeoutError,
    ModelUnavailableError,
)
from ai_career_navigator.models.providers import NvidiaNimProvider, configured_provider
from ai_career_navigator.models.providers.nvidia import NVIDIA_NIM_CHAT_COMPLETIONS_URL
from ai_career_navigator.models.schemas import ModelRequest, ModelResponse

MODEL = "nvidia/nemotron-3.5-lightning-30b-a3b"


class Person(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str


def _response(
    content: str = '{"name":"Ada"}',
    *,
    reasoning_content: str | None = "Here's a thinking process: private chain of thought",
) -> bytes:
    message: dict[str, object] = {"content": content}
    if reasoning_content is not None:
        message["reasoning_content"] = reasoning_content
    return json.dumps(
        {
            "id": "nim-request-123",
            "model": MODEL,
            "choices": [{"message": message, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 11, "completion_tokens": 5},
        }
    ).encode()


def test_configured_provider_routes_nvidia_without_changing_other_providers() -> None:
    nvidia = configured_provider(
        Settings(llm_provider="nvidia", nvidia_api_key="fake-nvidia-secret")
    )

    assert isinstance(nvidia, NvidiaNimProvider)
    assert nvidia.provider_name == "nvidia"


def test_extraction_disables_thinking_and_uses_json_mode() -> None:
    captured: dict[str, Any] = {}

    def http_post(url: str, headers: dict[str, str], body: bytes, timeout: float) -> bytes:
        captured.update(url=url, headers=headers, body=json.loads(body), timeout=timeout)
        return _response()

    provider = NvidiaNimProvider(SecretStr("fake-nvidia-secret"), http_post=http_post)
    request = ModelRequest(
        role=ModelRole.EXTRACTION,
        system_prompt="Return JSON",
        user_prompt="Extract a name",
        temperature=0.8,
        max_tokens=100,
        response_schema_name="Person",
    )
    response = provider.generate_structured(
        request=request,
        model=MODEL,
        output_schema=Person.model_json_schema(),
        timeout_seconds=12,
    )

    assert isinstance(response, ModelResponse)
    assert captured["url"] == NVIDIA_NIM_CHAT_COMPLETIONS_URL
    assert captured["timeout"] == 12
    assert captured["body"]["temperature"] == 0.0
    assert captured["body"]["chat_template_kwargs"] == {"enable_thinking": False}
    assert captured["body"]["response_format"] == {"type": "json_object"}
    schema_message = captured["body"]["messages"][1]["content"]
    assert "JSON Schema" in schema_message
    assert '"name"' in schema_message
    assert '"additionalProperties":false' in schema_message
    assert "reasoning_budget" not in captured["body"]


def test_reasoning_disables_visible_thinking_and_returns_only_final_content() -> None:
    captured: dict[str, Any] = {}

    def http_post(url: str, headers: dict[str, str], body: bytes, timeout: float) -> bytes:
        del url, headers, timeout
        captured.update(json.loads(body))
        return _response(content="Final answer")

    provider = NvidiaNimProvider("fake-nvidia-secret", http_post=http_post)
    response = provider.generate_text(
        request=ModelRequest(
            role=ModelRole.REASONING,
            user_prompt="Reason carefully",
            temperature=0.4,
            max_tokens=4096,
        ),
        model=MODEL,
        timeout_seconds=10,
    )

    assert captured["temperature"] == 0.4
    assert captured["chat_template_kwargs"] == {"enable_thinking": False}
    assert "reasoning_budget" not in captured
    assert "response_format" not in captured
    assert response.content == "Final answer"
    assert "Here's a thinking process:" not in response.content
    assert "private chain of thought" not in response.model_dump_json()


def test_gateway_validates_nvidia_structured_output_with_pydantic() -> None:
    provider = NvidiaNimProvider(
        "fake-nvidia-secret",
        http_post=lambda url, headers, body, timeout: _response(),
    )
    gateway = ModelGateway(
        provider=provider,
        models={ModelRole.EXTRACTION: MODEL},
        timeout_seconds=10,
        max_retries=0,
    )

    response = gateway.generate_structured(
        role=ModelRole.EXTRACTION,
        output_schema=Person,
        system_prompt="Return JSON",
        user_prompt="Extract a name",
    )

    assert response.structured_output == {"name": "Ada"}


def test_gateway_rejects_invalid_nvidia_structured_output() -> None:
    provider = NvidiaNimProvider(
        "fake-nvidia-secret",
        http_post=lambda url, headers, body, timeout: _response('{"wrong":"field"}'),
    )
    gateway = ModelGateway(
        provider=provider,
        models={ModelRole.EXTRACTION: MODEL},
        timeout_seconds=10,
        max_retries=0,
    )

    with pytest.raises(ModelResponseValidationError):
        gateway.generate_structured(
            role=ModelRole.EXTRACTION,
            output_schema=Person,
            system_prompt="Return JSON",
            user_prompt="Extract a name",
        )


def test_response_normalization_includes_usage_and_request_metadata() -> None:
    provider = NvidiaNimProvider(
        "fake-nvidia-secret",
        http_post=lambda url, headers, body, timeout: _response(content="Ready"),
    )

    response = provider.generate_text(
        request=ModelRequest(role=ModelRole.REASONING, user_prompt="Hello"),
        model=MODEL,
        timeout_seconds=10,
    )

    assert response.provider == "nvidia"
    assert response.model == MODEL
    assert response.role is ModelRole.REASONING
    assert response.request_id == "nim-request-123"
    assert response.finish_reason == "stop"
    assert response.input_tokens == 11
    assert response.output_tokens == 5
    assert response.latency_ms >= 0


def test_provider_representation_and_payload_do_not_expose_secret() -> None:
    secret = "fake-nvidia-secret-that-must-not-leak"
    captured_body = b""

    def http_post(url: str, headers: dict[str, str], body: bytes, timeout: float) -> bytes:
        nonlocal captured_body
        del url, headers, timeout
        captured_body = body
        return _response(content="Ready")

    provider = NvidiaNimProvider(secret, http_post=http_post)
    provider.generate_text(
        request=ModelRequest(role=ModelRole.REASONING, user_prompt="Hello"),
        model=MODEL,
        timeout_seconds=10,
    )

    assert secret not in repr(provider)
    assert secret not in str(provider)
    assert secret.encode() not in captured_body


@pytest.mark.parametrize(
    ("status_code", "error_type"),
    (
        (401, ModelAuthenticationError),
        (403, ModelAuthenticationError),
        (408, ModelTimeoutError),
        (429, ModelRateLimitError),
        (500, ModelUnavailableError),
        (422, ModelProviderError),
    ),
)
def test_http_failures_map_to_existing_gateway_errors(status_code, error_type) -> None:
    def failed(url: str, headers: dict[str, str], body: bytes, timeout: float) -> bytes:
        del headers, body, timeout
        raise HTTPError(url, status_code, "safe provider error", {}, None)

    provider = NvidiaNimProvider("fake-nvidia-secret", http_post=failed)

    with pytest.raises(error_type):
        provider.generate_text(
            request=ModelRequest(role=ModelRole.REASONING, user_prompt="Hello"),
            model=MODEL,
            timeout_seconds=10,
        )


@pytest.mark.parametrize(
    ("failure", "error_type"),
    (
        (TimeoutError("timed out"), ModelTimeoutError),
        (URLError("offline"), ModelUnavailableError),
        (ValueError("provider internals"), ModelProviderError),
    ),
)
def test_transport_failures_map_without_leaking_provider_details(failure, error_type) -> None:
    def failed(url: str, headers: dict[str, str], body: bytes, timeout: float) -> bytes:
        del url, headers, body, timeout
        raise failure

    provider = NvidiaNimProvider("fake-nvidia-secret", http_post=failed)

    with pytest.raises(error_type) as caught:
        provider.generate_text(
            request=ModelRequest(role=ModelRole.REASONING, user_prompt="Hello"),
            model=MODEL,
            timeout_seconds=10,
        )

    assert "provider internals" not in str(caught.value)
