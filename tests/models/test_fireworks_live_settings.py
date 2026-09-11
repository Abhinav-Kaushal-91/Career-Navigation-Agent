import json
import subprocess

import pytest

from ai_career_navigator.config import Settings
from ai_career_navigator.models import ModelGateway, ModelRole
from ai_career_navigator.models.errors import ModelTimeoutError, ModelUnavailableError
from ai_career_navigator.models.providers import FakeModelProvider, configured_provider
from ai_career_navigator.models.providers.fireworks import FireworksProvider
from ai_career_navigator.models.providers.fireworks_stream_worker import collect_stream
from ai_career_navigator.models.schemas import ModelRequest


def test_configured_output_override_reaches_provider():
    provider = FakeModelProvider(default_response="ok")
    settings = Settings(
        _env_file=None,
        llm_provider="fake",
        extraction_model="test",
        reasoning_model="test",
        model_max_output_tokens=30000,
    )
    gateway = ModelGateway.from_settings(settings, providers={"fake": provider})
    gateway.generate_text(
        role=ModelRole.EXTRACTION, system_prompt="", user_prompt="hello", max_tokens=100
    )
    assert provider.calls[0].request.max_tokens == 30000


def test_fireworks_streaming_selected_from_settings():
    settings = Settings(
        _env_file=None, llm_provider="fireworks", fireworks_api_key="test", fireworks_streaming=True
    )
    assert configured_provider(settings)._streaming is True


@pytest.mark.parametrize(
    ("model", "override", "expected"),
    [
        ("accounts/fireworks/models/glm-5p3-flash", None, "high"),
        ("accounts/fireworks/models/glm-5p3-flash", "medium", "medium"),
        ("other-model", None, None),
    ],
)
def test_reasoning_setting_reaches_the_actual_stream_body(monkeypatch, model, override, expected):
    observed = {}
    provider = FireworksProvider("test", streaming=True, reasoning_effort=override)

    def capture(payload, *args):
        observed.update(payload)
        return None

    monkeypatch.setattr(provider, "_stream_response", capture)
    provider.generate_text(
        request=ModelRequest(role=ModelRole.EXTRACTION, user_prompt="test", max_tokens=30000),
        model=model,
        timeout_seconds=5,
    )
    assert observed.get("reasoning_effort") == expected
    assert observed["max_tokens"] == 30000
    assert "test" not in str({key: value for key, value in observed.items() if key != "messages"})


def test_stream_discards_reasoning_and_preserves_length():
    result = collect_stream(
        [
            'data: {"choices":[{"delta":{"reasoning_content":"PRIVATE"}}]}',
            'data: {"choices":[{"delta":{"content":"{}"},"finish_reason":"length"}]}',
            'data: {"choices":[],"usage":{"prompt_tokens":10,"completion_tokens":30000}}',
            "data: [DONE]",
        ],
        "glm",
    )
    assert "PRIVATE" not in json.dumps(result)
    assert result["choices"][0]["finish_reason"] == "length"
    assert result["usage"]["completion_tokens"] == 30000


def test_stream_without_finish_is_rejected():
    with pytest.raises(ValueError, match="incomplete"):
        collect_stream(['data: {"choices":[{"delta":{"content":"{}"}}]}'], "glm")


def test_deadline_kills_worker_and_discards_partial_output(monkeypatch):
    class Process:
        killed = False

        def communicate(self, data=None, timeout=None):
            if not self.killed:
                raise subprocess.TimeoutExpired("worker", timeout)
            return b"partial output", None

        def kill(self):
            self.killed = True

    process = Process()
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: process)
    provider = FireworksProvider("test", streaming=True)
    with pytest.raises(ModelTimeoutError):
        provider.generate_text(
            request=ModelRequest(role=ModelRole.REASONING, user_prompt="test"),
            model="glm",
            timeout_seconds=0.1,
        )
    assert process.killed


@pytest.mark.parametrize(
    ("category", "expected"), [("timeout", ModelTimeoutError), ("transport", ModelUnavailableError)]
)
def test_worker_transport_errors_keep_safe_category(monkeypatch, category, expected):
    class Process:
        def communicate(self, *args, **kwargs):
            return json.dumps({"worker_error": category}).encode(), None

    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: Process())
    with pytest.raises(expected):
        FireworksProvider("secret-test", streaming=True).generate_text(
            request=ModelRequest(role=ModelRole.EXTRACTION, user_prompt="test"),
            model="glm",
            timeout_seconds=1,
        )
