import json
from typing import Any

import pytest
from pydantic import SecretStr

from ai_career_navigator.models import ModelAuthenticationError, ModelRole
from ai_career_navigator.models.providers import FireworksProvider
from ai_career_navigator.models.schemas import ModelRequest, ModelResponse


def test_fireworks_response_is_normalized_and_private_reasoning_is_discarded() -> None:
    captured: dict[str, Any] = {}

    def http_post(url: str, headers: dict[str, str], body: bytes, timeout: float) -> bytes:
        captured.update(url=url, headers=headers, body=json.loads(body), timeout=timeout)
        return json.dumps(
            {
                "id": "request-123",
                "model": "accounts/fireworks/models/test-model",
                "choices": [
                    {
                        "message": {
                            "content": '{"name":"Ada"}',
                            "reasoning_content": "private provider reasoning",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 7, "completion_tokens": 4},
            }
        ).encode()

    provider = FireworksProvider(SecretStr("fake-api-key"), http_post=http_post)
    request = ModelRequest(
        role=ModelRole.EXTRACTION,
        system_prompt="Return JSON",
        user_prompt="Extract a name",
        response_schema_name="Person",
    )
    response = provider.generate_structured(
        request=request,
        model="accounts/fireworks/models/test-model",
        output_schema={"type": "object", "properties": {"name": {"type": "string"}}},
        timeout_seconds=12,
    )

    assert isinstance(response, ModelResponse)
    assert response.request_id == "request-123"
    assert response.input_tokens == 7
    assert response.output_tokens == 4
    assert captured["timeout"] == 12
    assert captured["body"]["response_format"]["type"] == "json_schema"
    assert "private provider reasoning" not in response.model_dump_json()


def test_fireworks_provider_representation_never_contains_secret() -> None:
    provider = FireworksProvider("fake-secret")

    assert "fake-secret" not in repr(provider)
    assert "fake-secret" not in str(provider)


def test_fireworks_authentication_status_becomes_typed_error() -> None:
    def unauthorized(url: str, headers: dict[str, str], body: bytes, timeout: float) -> bytes:
        del url, headers, body, timeout
        from urllib.error import HTTPError

        raise HTTPError("https://example.invalid", 401, "Unauthorized", {}, None)

    provider = FireworksProvider("fake-secret", http_post=unauthorized)
    request = ModelRequest(role=ModelRole.REASONING, user_prompt="Hello")

    with pytest.raises(ModelAuthenticationError):
        provider.generate_text(request=request, model="test-model", timeout_seconds=10)
