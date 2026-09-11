import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize("effort", ["none", "high"])
def test_only_reasoning_setting_changes_and_only_one_request(monkeypatch, tmp_path, effort):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "scripts"))
    module = importlib.import_module("benchmark_glm_reasoning_control")
    captured = []

    def transport(self, payload, request, model, timeout_seconds):
        captured.append(payload)
        return SimpleNamespace(
            content='{"ok":true}', finish_reason="stop", input_tokens=10, output_tokens=5
        )

    monkeypatch.setattr(module.FireworksProvider, "_stream_response", transport)
    reference = {"model": "fake", "max_tokens": 30000, "messages": []}
    provider = module.ControlledProvider("fake-test-key", tmp_path, reference, effort)
    provider._stream_response(dict(reference), None, "fake", 600)
    assert captured == [{**reference, "reasoning_effort": effort}]
    assert "reasoning_effort" not in reference
    with pytest.raises(module.ModelProviderError):
        provider._stream_response(dict(reference), None, "fake", 600)
    assert len(captured) == 1


def test_changed_control_request_is_not_sent(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "scripts"))
    module = importlib.import_module("benchmark_glm_reasoning_control")
    provider = module.ControlledProvider("fake-test-key", tmp_path, {"model": "expected"})
    with pytest.raises(module.ModelProviderError, match="differs from control"):
        provider._stream_response({"model": "wrong"}, None, "wrong", 600)
    assert provider.calls == 0
