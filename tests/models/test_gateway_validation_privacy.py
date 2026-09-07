"""Invalid response field names must not escape the structured model boundary."""

import json
import logging
import traceback

import pytest
from pydantic import BaseModel, ConfigDict

from ai_career_navigator.models import ModelGateway, ModelResponseValidationError, ModelRole
from ai_career_navigator.models.inspection import LocalModelInspector
from ai_career_navigator.models.providers import FakeModelProvider


class Entry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str
    count: int


class NestedResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entries: list[Entry]
    by_name: dict[str, Entry]


def invoke(provider, schema, *, inspector=None):
    gateway = ModelGateway(
        provider=provider,
        models={ModelRole.EXTRACTION: "privacy-test"},
        timeout_seconds=5,
        max_retries=1,
        sleeper=lambda _: None,
        inspector=inspector,
    )
    return gateway.generate_structured(
        role=ModelRole.EXTRACTION,
        output_schema=schema,
        system_prompt="Return the required structured object.",
        user_prompt="Synthetic privacy regression input.",
    )


@pytest.mark.parametrize("inspector_enabled", [False, True])
def test_untrusted_extra_keys_never_reach_logs_repair_or_inspector(caplog, inspector_enabled):
    private_key = "private.person@example.test SECRET_PAYLOAD_AS_FIELD_NAME"
    private_value = "NEVER_RETAIN_THE_INVALID_RESPONSE_VALUE"
    payload = json.dumps({"status": "ready", "count": 1, private_key: private_value})
    provider = FakeModelProvider(outcomes=[payload, payload])
    inspector = LocalModelInspector() if inspector_enabled else None
    with caplog.at_level(logging.INFO), pytest.raises(ModelResponseValidationError) as raised:
        invoke(provider, Entry, inspector=inspector)

    repairs = " ".join(call.request.system_prompt for call in provider.calls)
    exposed = " ".join(
        [
            caplog.text,
            repairs,
            str(raised.value),
            "".join(traceback.format_exception(raised.value)),
            json.dumps(inspector.events if inspector else []),
        ]
    )
    assert private_key not in exposed
    assert "private.person@example.test" not in exposed
    assert private_value not in exposed
    assert "<unexpected-field>:extra_forbidden" in repairs
    assert "<unexpected-field>:extra_forbidden" in caplog.text
    assert len(provider.calls) == 2


def test_nested_regular_fields_and_array_indices_remain_diagnostic(caplog):
    payload = json.dumps({"entries": [{"status": "ready", "count": "not-a-number"}], "by_name": {}})
    provider = FakeModelProvider(outcomes=[payload, payload])
    with caplog.at_level(logging.INFO), pytest.raises(ModelResponseValidationError):
        invoke(provider, NestedResult)
    assert "entries.0.count:int_parsing" in caplog.text
    assert "entries.0.count:int_parsing" in provider.calls[1].request.system_prompt
    assert "not-a-number" not in caplog.text


@pytest.mark.parametrize("dynamic_key", ["user@example.test", "status", "9912345"])
def test_dynamic_dictionary_keys_are_redacted_at_their_schema_location(caplog, dynamic_key):
    payload = json.dumps(
        {"entries": [], "by_name": {dynamic_key: {"status": "ready", "count": "bad"}}}
    )
    provider = FakeModelProvider(outcomes=[payload, payload])
    with caplog.at_level(logging.INFO), pytest.raises(ModelResponseValidationError):
        invoke(provider, NestedResult)
    repairs = provider.calls[1].request.system_prompt
    assert "by_name.<unexpected-field>.count:int_parsing" in repairs
    assert f"by_name.{dynamic_key}." not in repairs
    assert f"by_name.{dynamic_key}." not in caplog.text


def test_enabled_inspector_redacts_nested_dynamic_keys_without_changing_original_payload():
    secret = "configured-inspector-secret-value"
    contact = "private.person@example.test"
    original = {contact: {secret: "safe-value"}}
    inspector = LocalModelInspector(secrets=(secret,))
    inspector.record("validated_response", payload=original)
    retained = inspector.events[0]["payload"]
    assert retained == {"[CONTACT REDACTED]": {"[REDACTED]": "safe-value"}}
    assert secret not in json.dumps(inspector.events)
    assert contact not in json.dumps(inspector.events)
    assert original == {contact: {secret: "safe-value"}}
