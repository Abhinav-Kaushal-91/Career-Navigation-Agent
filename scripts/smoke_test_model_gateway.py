"""Explicit, manual-only smoke test for the configured Fireworks model gateway."""

from ai_career_navigator.config import get_settings
from ai_career_navigator.models import ModelGateway, ModelRole


def main() -> None:
    settings = get_settings()
    if settings.llm_provider != "fireworks":
        raise SystemExit("Set LLM_PROVIDER=fireworks before running this manual smoke test.")
    if settings.fireworks_api_key is None:
        raise SystemExit("FIREWORKS_API_KEY is required. The key will not be printed.")

    response = ModelGateway.from_settings(settings).generate_text(
        role=ModelRole.REASONING,
        system_prompt="Answer concisely.",
        user_prompt="Reply with exactly: model gateway ready",
        temperature=0,
        max_tokens=16,
        metadata={"task_type": "manual_smoke_test"},
    )
    print(f"provider={response.provider} model={response.model}")
    print(response.content[:200])


if __name__ == "__main__":
    main()
