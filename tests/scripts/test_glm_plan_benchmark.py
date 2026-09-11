import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest


def module(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "scripts"))
    return importlib.import_module("benchmark_glm_plan")


def test_plan_transport_is_one_call_and_saves_actual_high_payload(monkeypatch, tmp_path):
    subject = module(monkeypatch)
    captured = []

    def transport(self, payload, request, model, timeout_seconds):
        captured.append(payload)
        return SimpleNamespace(
            content='{"milestones":[]}', finish_reason="stop", input_tokens=10, output_tokens=5
        )

    monkeypatch.setattr(subject.FireworksProvider, "_stream_response", transport)
    provider = subject.PlanProvider("fake-test-key", tmp_path)
    original = {"model": "fake", "max_tokens": 30000, "messages": []}
    provider._stream_response(original, None, "fake", 600)
    assert captured == [{**original, "reasoning_effort": "high"}]
    assert "reasoning_effort" not in original
    assert subject.json.loads((tmp_path / "request.json").read_text()) == captured[0]
    with pytest.raises(subject.ModelProviderError):
        provider._stream_response(original, None, "fake", 600)


def test_immutable_audit_ignores_only_two_wording_fields(monkeypatch):
    subject = module(monkeypatch)
    source = {
        "target_role": "Example",
        "milestones": [
            {"action": "Act", "measurable_outcome": "Check", "linked_gap_ids": ["gap-1"]}
        ],
    }
    plan = SimpleNamespace(
        model_dump=lambda **kwargs: subject.json.loads(subject.json.dumps(source))
    )
    result = subject.immutable_view(plan)
    assert result == {"target_role": "Example", "milestones": [{"linked_gap_ids": ["gap-1"]}]}
    assert source["milestones"][0]["action"] == "Act"
