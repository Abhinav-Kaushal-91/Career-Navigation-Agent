from ai_career_navigator.config import Settings
from ai_career_navigator.models import ModelRole
from ai_career_navigator.models.providers import FakeModelProvider
from ai_career_navigator.ui.live_workflow import build_live_workflow_runtime


def test_blank_validation_model_uses_live_reasoning_model(monkeypatch) -> None:
    provider = FakeModelProvider(outcomes=["validated"])
    monkeypatch.setattr(
        "ai_career_navigator.ui.live_workflow.configured_provider", lambda _settings: provider
    )
    runtime = build_live_workflow_runtime(
        Settings(
            llm_provider="mock",
            extraction_model="extract-model",
            reasoning_model="reason-model",
            validation_model="",
        )
    )

    response = runtime.model_gateway.generate_text(
        role=ModelRole.VALIDATION,
        system_prompt="Validate one bounded decision.",
        user_prompt="Return the decision.",
    )

    assert response.model == "reason-model"
    assert provider.calls[0].model == "reason-model"
