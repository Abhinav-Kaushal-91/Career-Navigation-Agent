"""Environment-backed application configuration."""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration shared by application and infrastructure boundaries.

    Provider credentials are optional until their integration activities begin.
    ``SecretStr`` prevents their values from appearing in normal model output.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = "development"
    log_level: str = "INFO"

    ydc_api_key: SecretStr | None = None
    fireworks_api_key: SecretStr | None = None
    nvidia_api_key: SecretStr | None = None
    hf_token: SecretStr | None = None

    llm_provider: str = "mock"
    extraction_model: str = "mock-extraction"
    reasoning_model: str = "mock-reasoning"
    validation_model: str = "mock-validation"
    model_timeout_seconds: int = 60
    max_retries: int = 2

    database_path: Path = Path("data/local/career_navigator.db")
    checkpoint_database_path: Path = Path("data/local/langgraph_checkpoints.db")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        """Normalize and validate standard logging levels."""

        normalized = value.upper()
        allowed_levels = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
        if normalized not in allowed_levels:
            message = f"LOG_LEVEL must be one of {sorted(allowed_levels)}"
            raise ValueError(message)
        return normalized


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide immutable configuration source."""

    return Settings()
