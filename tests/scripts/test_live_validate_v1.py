import asyncio
import json
from types import SimpleNamespace

import pytest

from ai_career_navigator.config import Settings
from ai_career_navigator.models import ModelRole
from ai_career_navigator.models.inspection import LocalModelInspector
from ai_career_navigator.models.providers import FakeModelProvider
from ai_career_navigator.models.tracking import ModelUsage
from scripts import live_validate_v1 as live


class RecordingProvider:
    provider_name = "nvidia"

    def __init__(self):
        self.calls = []

    def generate_text(self, **kwargs):
        self.calls.append(kwargs)
        return "final text"

    def generate_structured(self, **kwargs):
        self.calls.append(kwargs)
        return {"final": "structured"}


def test_cli_refuses_calls_without_explicit_allow_live(monkeypatch):
    def forbidden(*args):
        raise AssertionError("must not initialize live providers")

    monkeypatch.setattr(live, "run_once", forbidden)
    with pytest.raises(SystemExit) as error:
        live.main([])
    assert error.value.code == 2


def test_budget_limits_actual_invocations_and_public_provider_timeouts():
    inner = RecordingProvider()
    budget = live.BudgetModelProvider(inner, max_calls=2, clock=lambda: 0)
    assert budget.provider_name == "nvidia"
    assert budget.generate_text(request="a", model="nvidia", timeout_seconds=90) == "final text"
    assert budget.generate_structured(
        request="b", model="nvidia", output_schema={"type": "object"}, timeout_seconds=12
    ) == {"final": "structured"}
    with pytest.raises(live.LiveModelBudgetExceeded) as error:
        budget.generate_text(request="c", model="nvidia", timeout_seconds=10)
    assert error.value.retryable is False
    assert len(inner.calls) == budget.calls == 2
    assert budget.stops == 1
    assert [call["timeout_seconds"] for call in inner.calls] == [60, 12]
    assert inner.calls[1]["output_schema"] == {"type": "object"}


def test_budget_enforces_remaining_total_deadline():
    now = [0.0]
    inner = RecordingProvider()
    budget = live.BudgetModelProvider(inner, deadline_seconds=600, clock=lambda: now[0])
    now[0] = 592
    budget.generate_text(request="a", model="nvidia", timeout_seconds=60)
    assert inner.calls[0]["timeout_seconds"] == 8
    now[0] = 600
    with pytest.raises(live.LiveModelBudgetExceeded):
        budget.generate_text(request="b", model="nvidia", timeout_seconds=60)
    assert len(inner.calls) == 1


def test_bounded_settings_disclose_limits_without_secrets(tmp_path):
    base = Settings(
        _env_file=None,
        nvidia_api_key="private-secret",
        max_retries=3,
        model_timeout_seconds=120,
        langsmith_tracing=True,
    )
    settings, changes = live.bounded_settings(base, tmp_path / "result.json")
    assert settings.market_analysis_posting_limit == 5
    assert settings.market_max_total_search_calls == 6
    assert settings.market_max_content_fetches == 12
    assert settings.max_retries == 1
    assert settings.model_timeout_seconds == 60
    assert settings.market_timeout_seconds <= 30
    assert not settings.langsmith_tracing
    assert settings.model_inspector_enabled
    assert changes["model_timeout_seconds"] == {"production": "120", "live_validation": "60"}
    assert "private-secret" not in json.dumps(changes)
    assert base.max_retries == 3


def test_only_synthetic_same_role_candidate_and_untimed_goal_are_used():
    profile, goal = live.synthetic_inputs()
    data = profile.model_dump(mode="json")
    target = goal.model_dump(mode="json")
    assert "Senior Java Developer" in json.dumps(data)
    assert target["target_role"] == "Senior Java Developer"
    assert "Toronto" in json.dumps(target)
    assert target["target_timeline_months"] is None
    assert "SYNTHETIC_FROZEN_FIXTURE" in json.dumps(data)
    assert "APPLY_NOW" not in json.dumps(data)
    assert "expected_accessibility" not in json.dumps(data)


def test_shared_runtime_uses_public_override_and_preserves_usage_tracking(monkeypatch):
    provider = FakeModelProvider(outcomes=["validated"])

    def forbidden(*args):
        raise AssertionError("a provider override must not create another provider")

    monkeypatch.setattr("ai_career_navigator.ui.live_workflow.configured_provider", forbidden)
    runtime = live.build_live_workflow_runtime(
        Settings(_env_file=None, llm_provider="mock", reasoning_model="reason-model"),
        provider_override=provider,
    )
    response = runtime.model_gateway.generate_text(
        role=ModelRole.REASONING, system_prompt="Synthetic", user_prompt="One decision"
    )
    assert response.model == "reason-model"
    assert runtime.model_usage.calls == runtime.model_usage.successful_calls == 1


def test_partial_live_state_and_sanitized_inspector_export_on_failure(monkeypatch, tmp_path):
    base = Settings(_env_file=None, llm_provider="nvidia", nvidia_api_key="private-secret")
    inspector = LocalModelInspector()
    inspector.record(
        "response", content="safe", chain_of_thought="hidden", api_key="private-secret"
    )
    partial = {
        "current_stage": "CAREER_ASSESSMENT_SYNTHESIS_READY",
        "workflow_status": "RUNNING",
        "career_assessment_synthesis": {"accessibility": "ASPIRATIONAL"},
        "market_snapshot": {"validated_posting_count": 3},
        "public_source": "public text",
    }

    class PartialController:
        async def stream_start(self, **kwargs):
            assert kwargs["capability_inference_requested"] is False
            assert kwargs["confirmed_goal"].target_role == "Senior Java Developer"
            yield "market_processing"
            raise TimeoutError("private-secret was not printed")

        def inspect(self, **kwargs):
            return SimpleNamespace(state=partial)

    def factory(settings, *, provider_override):
        assert isinstance(provider_override, live.BudgetModelProvider)
        assert settings.market_max_total_search_calls == 6
        return SimpleNamespace(
            controller=PartialController(),
            model_usage=ModelUsage(),
            model_gateway=SimpleNamespace(inspector=inspector),
        )

    monkeypatch.setattr(live, "load_live_settings", lambda: base)
    monkeypatch.setattr(live, "configured_provider", lambda settings: RecordingProvider())
    monkeypatch.setattr(live, "build_live_workflow_runtime", factory)
    output = tmp_path / "result.json"
    result = asyncio.run(live.run_once(output))
    assert result["failure"]["category"] == "TimeoutError"
    assert result["actual_accessibility"] == "ASPIRATIONAL"
    assert result["validated_postings"] == 3
    assert result["graph_state"] == partial
    assert result["progress"][0]["stage"] == "market_processing"
    assert "private-secret" not in output.read_text(encoding="utf-8")
    assert "chain_of_thought" not in output.read_text(encoding="utf-8")
    assert result["actual_model_provider_invocations"] == 0
