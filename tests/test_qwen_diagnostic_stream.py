"""Offline checks for diagnostic streaming; no inference requests."""

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

from pydantic import SecretStr

from ai_career_navigator.models import ModelRole
from ai_career_navigator.models.errors import ModelProviderError
from ai_career_navigator.models.schemas import ModelRequest


def load_script(monkeypatch):
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location(
        "qwen_diagnostic_test", scripts / "run_qwen_saved_market.py"
    )
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    return module


def test_stream_assembles_only_final_content_and_usage(monkeypatch, tmp_path):
    module = load_script(monkeypatch)
    packets = [
        SimpleNamespace(
            usage=None,
            choices=[
                SimpleNamespace(
                    delta=SimpleNamespace(content='{"ok":', reasoning_content="PRIVATE_TRACE"),
                    finish_reason=None,
                )
            ],
        ),
        SimpleNamespace(
            usage=SimpleNamespace(prompt_tokens=11, completion_tokens=5),
            choices=[SimpleNamespace(delta=SimpleNamespace(content="true}"), finish_reason="stop")],
        ),
    ]
    sent = []

    class Client:
        def __init__(self, **kwargs):
            pass

        def chat_completion(self, **kwargs):
            sent.append(kwargs)
            return iter(packets)

    monkeypatch.setattr(module, "InferenceClient", Client)
    provider = module.StreamingDiagnosticProvider(SecretStr("test-secret"), tmp_path)
    response = provider.generate_structured(
        request=ModelRequest(
            role=ModelRole.EXTRACTION,
            system_prompt="Original instruction",
            user_prompt="Original posting",
        ),
        model=module.MODEL,
        output_schema={"type": "object"},
        timeout_seconds=60,
    )
    assert response.content == '{"ok":true}'
    assert response.input_tokens == 11
    assert response.output_tokens == 5
    assert sent[0]["stream"] is True
    assert sent[0]["max_tokens"] == 20000
    assert [m["role"] for m in sent[0]["messages"]] == ["system", "user"]
    for path in tmp_path.rglob("*"):
        if path.is_file():
            assert "PRIVATE_TRACE" not in path.read_text()
            assert "test-secret" not in path.read_text()


def test_failure_redacts_secret_and_records_no_partial_response(monkeypatch, tmp_path):
    module = load_script(monkeypatch)

    class Client:
        def __init__(self, **kwargs):
            pass

        def chat_completion(self, **kwargs):
            raise RuntimeError("Rejected hf_testcredential")

    monkeypatch.setattr(module, "InferenceClient", Client)
    provider = module.StreamingDiagnosticProvider(SecretStr("hf_testcredential"), tmp_path)
    try:
        provider.generate_structured(
            request=ModelRequest(role=ModelRole.EXTRACTION, user_prompt="posting"),
            model=module.MODEL,
            output_schema={"type": "object"},
            timeout_seconds=60,
        )
    except ModelProviderError:
        pass
    else:
        raise AssertionError("Expected safe failure")
    failure = json.loads((tmp_path / "call-01/failure.json").read_text())
    assert "hf_testcredential" not in failure["sanitized_message"]
    assert provider.failures == 1
    assert not (tmp_path / "call-01/response.txt").exists()


def test_fireworks_uses_direct_sse_and_discards_reasoning(monkeypatch):
    module = load_script(monkeypatch)
    captured = {}

    class Response:
        is_error = False

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def iter_lines(self):
            yield 'data: {"choices":[{"delta":{"reasoning_content":"PRIVATE"}}]}'
            yield (
                'data: {"choices":[{"delta":{"content":"{}"},"finish_reason":"stop"}],'
                '"usage":{"prompt_tokens":4,"completion_tokens":2}}'
            )
            yield "data: [DONE]"

    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def stream(self, method, url, **kwargs):
            captured.update(method=method, url=url, **kwargs)
            return Response()

    monkeypatch.setattr(module.httpx, "Client", Client)
    chunks = list(
        module.FireworksStreamClient(api_key="test", timeout=60).chat_completion(
            model="accounts/fireworks/models/glm-5p3-flash",
            stream=True,
            extra_body={"chat_template_kwargs": {"enable_thinking": True}},
        )
    )
    assert captured["url"] == "https://api.fireworks.ai/inference/v1/chat/completions"
    assert "extra_body" not in captured["json"]
    assert captured["json"]["chat_template_kwargs"]["enable_thinking"] is True
    assert chunks[0].choices[0].delta.content is None
    assert not hasattr(chunks[0].choices[0].delta, "reasoning_content")
    assert chunks[1].choices[0].delta.content == "{}"
    assert chunks[1].usage.completion_tokens == 2
