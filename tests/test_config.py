from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from ai_career_navigator.config import Settings, get_settings


def test_settings_defaults() -> None:
    settings = Settings()

    assert settings.app_env == "development"
    assert settings.log_level == "INFO"
    assert settings.ydc_api_key is None
    assert settings.you_mcp_url == "https://api.you.com/mcp"
    assert settings.adzuna_app_id is None
    assert settings.adzuna_app_key is None
    assert settings.adzuna_base_url == "https://api.adzuna.com/v1/api"
    assert settings.market_primary_provider == "jsearch"
    assert settings.market_enrichment_provider == "none"
    assert settings.rapidapi_key is None
    assert settings.market_timeout_seconds == 30
    assert settings.market_max_search_queries == 3
    assert settings.market_max_expansion_queries == 3
    assert settings.market_max_content_fetches == 30
    assert settings.market_target_posting_count == 20
    assert settings.market_analysis_posting_limit == 10
    assert settings.market_expansion_threshold == 8
    assert settings.llm_provider == "mock"
    assert settings.extraction_model == "mock-extraction"
    assert settings.reasoning_model == "mock-reasoning"
    assert settings.validation_model == "mock-validation"
    assert settings.model_timeout_seconds == 90
    assert settings.max_retries == 2
    assert settings.database_path == Path("data/local/career_navigator.db")
    assert settings.checkpoint_database_path == Path("data/local/langgraph_checkpoints.db")


def test_settings_environment_override(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("YDC_API_KEY", "fake-you-key")
    monkeypatch.setenv("MARKET_MAX_CONTENT_FETCHES", "25")
    monkeypatch.setenv("LLM_PROVIDER", "fireworks")
    monkeypatch.setenv("EXTRACTION_MODEL", "nvidia-nemotron")
    monkeypatch.setenv("REASONING_MODEL", "llama-3.1")
    monkeypatch.setenv("VALIDATION_MODEL", "validator")
    monkeypatch.setenv("MODEL_TIMEOUT_SECONDS", "90")
    monkeypatch.setenv("MAX_RETRIES", "4")

    settings = Settings()

    assert settings.app_env == "test"
    assert settings.log_level == "DEBUG"
    assert settings.ydc_api_key == SecretStr("fake-you-key")
    assert settings.market_max_content_fetches == 25
    assert settings.llm_provider == "fireworks"
    assert settings.extraction_model == "nvidia-nemotron"
    assert settings.reasoning_model == "llama-3.1"
    assert settings.validation_model == "validator"
    assert settings.model_timeout_seconds == 90
    assert settings.max_retries == 4


def test_get_settings_uses_global_singleton(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("LLM_PROVIDER", "huggingface")

    first = get_settings()
    second = get_settings()

    assert first.llm_provider == "huggingface"
    assert first is second
    get_settings.cache_clear()


def test_secret_representation(monkeypatch) -> None:
    fake_secret = "fake-fireworks-secret"
    monkeypatch.setenv("FIREWORKS_API_KEY", fake_secret)

    settings = Settings()

    assert fake_secret not in repr(settings)
    assert fake_secret not in str(settings)
    assert "**********" in repr(settings)


def test_adzuna_secrets_are_redacted(monkeypatch) -> None:
    monkeypatch.setenv("ADZUNA_APP_ID", "private-adzuna-id")
    monkeypatch.setenv("ADZUNA_APP_KEY", "private-adzuna-key")
    settings = Settings()
    rendered = repr(settings)
    assert "private-adzuna-id" not in rendered
    assert "private-adzuna-key" not in rendered


@pytest.mark.parametrize(
    "overrides",
    (
        {"model_timeout_seconds": 0},
        {"max_retries": -1},
        {"max_retries": 6},
        {"llm_provider": " "},
        {"you_mcp_url": "http://api.you.com/mcp"},
        {"market_max_content_fetches": 0},
        {"market_analysis_posting_limit": 2},
        {"market_analysis_posting_limit": 11},
    ),
)
def test_invalid_model_gateway_settings_fail_fast(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        Settings(**overrides)
