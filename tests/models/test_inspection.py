import json

import pytest
from pydantic import BaseModel, ConfigDict

from ai_career_navigator.config import Settings
from ai_career_navigator.models import ModelGateway, ModelResponseValidationError, ModelRole
from ai_career_navigator.models.inspection import LocalModelInspector
from ai_career_navigator.models.providers import FakeModelProvider, NvidiaNimProvider
from ai_career_navigator.models.schemas import ModelResponse


class Result(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str


def test_inspector_disabled_by_default() -> None:
    assert (
        ModelGateway.from_settings(
            Settings(_env_file=None), providers={"mock": FakeModelProvider()}
        ).inspector
        is None
    )


def test_inspector_uses_actual_wire_body_and_excludes_credentials_and_private_trace() -> None:
    captured = {}

    def post(url, headers, body, timeout):
        captured.update(body=json.loads(body), timeout=timeout)
        return json.dumps(
            {
                "model": "test-model",
                "choices": [
                    {
                        "message": {
                            "content": '{"status":"ready"}',
                            "reasoning_content": "PRIVATE",
                        },
                        "finish_reason": "stop",
                    }
                ],
            }
        ).encode()

    recorder = LocalModelInspector(secrets=("top-secret",))
    provider = NvidiaNimProvider("top-secret", http_post=post)
    gateway = ModelGateway(
        provider=provider,
        models={ModelRole.EXTRACTION: "test-model"},
        timeout_seconds=17,
        max_retries=1,
        inspector=recorder,
    )
    gateway.generate_structured(
        role=ModelRole.EXTRACTION,
        output_schema=Result,
        system_prompt="Extract one field",
        user_prompt="status is ready",
        temperature=0.9,
        max_tokens=123,
        metadata={"prompt_version": "test-v1"},
    )
    request, response = recorder.events
    assert request["payload"] == captured["body"]
    assert request["payload"]["temperature"] == 0
    assert request["payload"]["chat_template_kwargs"] == {"enable_thinking": False}
    assert request["timeout_seconds"] == 17
    assert request["max_retries"] == 1
    assert response["structured_output"] == {"status": "ready"}
    assert "top-secret" not in json.dumps(recorder.events)
    assert "PRIVATE" not in json.dumps(recorder.events)
    assert "Authorization" not in json.dumps(recorder.events)


def test_invalid_response_is_not_retained_and_schema_retry_is_recorded() -> None:
    recorder = LocalModelInspector()
    provider = FakeModelProvider(outcomes=["MALFORMED_PRIVATE_TEXT", '{"status":"ready"}'])
    gateway = ModelGateway(
        provider=provider,
        models={ModelRole.EXTRACTION: "test-model"},
        timeout_seconds=10,
        max_retries=2,
        inspector=recorder,
        sleeper=lambda _: None,
    )
    gateway.generate_structured(
        role=ModelRole.EXTRACTION,
        output_schema=Result,
        system_prompt="Extract one field",
        user_prompt="status is ready",
    )
    assert [item["event"] for item in recorder.events] == [
        "request",
        "rejected_response",
        "request",
        "validated_response",
    ]
    assert recorder.events[2]["metadata"]["structured_retry"] is True
    assert "MALFORMED_PRIVATE_TEXT" not in json.dumps(recorder.events)


def test_valid_json_with_truncation_flag_is_rejected() -> None:
    response = ModelResponse(
        content='{"status":"ready"}',
        provider="mock",
        model="test-model",
        role=ModelRole.EXTRACTION,
        latency_ms=1,
        finish_reason="length",
    )
    with pytest.raises(ModelResponseValidationError, match="truncated_response"):
        ModelGateway._validated_response(response, Result)


def test_inspector_is_bounded_redacted_and_copied() -> None:
    recorder = LocalModelInspector(secrets=("credential-value",), max_events=2)
    recorder.record("first", raw="credential-value")
    recorder.record("second", authorization="Bearer key", email="test@example.com")
    recorder.record("third", reasoning_content="hidden", text="Bearer unsafe")
    events = recorder.events
    assert len(events) == 2
    assert "credential-value" not in json.dumps(events)
    assert "hidden" not in json.dumps(events)
    assert "test@example.com" not in json.dumps(events)
    assert "unsafe" not in json.dumps(events)
    events[0]["event"] = "changed"
    assert recorder.events[0]["event"] == "second"


def test_settings_validation_fallback_and_retry_parity() -> None:
    recorder_settings = Settings(
        _env_file=None,
        llm_provider="mock",
        validation_model=None,
        reasoning_model="test-model",
        max_retries=0,
        model_inspector_enabled=True,
    )
    gateway = ModelGateway.from_settings(recorder_settings, providers={"mock": FakeModelProvider()})
    gateway.generate_text(role=ModelRole.VALIDATION, system_prompt="", user_prompt="ready")
    assert gateway.inspector.events[0]["payload"]["neutral_request"]["role"] == "VALIDATION"
    assert gateway.inspector.events[0]["max_retries"] == 0
