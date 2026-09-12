"""Environment-backed application configuration."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
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
    you_mcp_url: str = "https://api.you.com/mcp"
    adzuna_app_id: SecretStr | None = None
    adzuna_app_key: SecretStr | None = None
    adzuna_base_url: str = "https://api.adzuna.com/v1/api"
    market_primary_provider: str = "jsearch"
    market_enrichment_provider: str = "none"
    rapidapi_key: SecretStr | None = None
    jsearch_search_path: Literal["/search", "/search-v2"] = "/search-v2"
    jsearch_country: str = Field(default="ca", pattern=r"^[a-z]{2}$")
    jsearch_max_details: int = Field(default=5, ge=0, le=10)
    jsearch_search_timeout_seconds: int = Field(default=90, ge=30, le=180)
    market_timeout_seconds: int = Field(default=30, gt=0, le=300)
    market_max_search_queries: int = Field(default=3, ge=1, le=10)
    market_max_expansion_queries: int = Field(default=3, ge=0, le=10)
    market_max_content_fetches: int = Field(default=30, ge=1, le=100)
    market_max_total_search_calls: int = Field(default=12, ge=2, le=30)
    market_max_posting_age_days: int = Field(default=90, ge=1, le=366)
    market_target_posting_count: int = Field(default=20, ge=1, le=100)
    market_analysis_posting_limit: int = Field(default=10, ge=3, le=10)
    market_max_enrichments: int | None = Field(default=None, ge=0, le=100)
    market_expansion_threshold: int = Field(default=8, ge=1, le=100)
    market_discovery_result_count: int = Field(default=12, ge=10, le=15)
    market_thin_description_characters: int = Field(default=500, ge=100, le=5000)
    market_direct_excluded_domains: list[str] = Field(
        default_factory=lambda: [
            "ziprecruiter.com",
            "indeed.com",
            "glassdoor.com",
            "glassdoor.ca",
            "linkedin.com",
            "jobilize.com",
        ]
    )
    fireworks_api_key: SecretStr | None = None
    nvidia_api_key: SecretStr | None = None
    hf_token: SecretStr | None = None

    llm_provider: str = "mock"
    extraction_model: str = "mock-extraction"
    reasoning_model: str = "mock-reasoning"
    validation_model: str | None = "mock-validation"
    model_timeout_seconds: int = Field(default=90, gt=0, le=600)
    model_max_output_tokens: int | None = Field(default=None, gt=0, le=131072)
    fireworks_streaming: bool = False
    fireworks_reasoning_effort: Literal["low", "medium", "high"] | None = None
    max_retries: int = Field(default=2, ge=0, le=5)
    model_inspector_enabled: bool = False

    langsmith_api_key: SecretStr | None = None
    langsmith_tracing: bool = False
    langsmith_project: str | None = None
    langsmith_workspace_id: str | None = None
    langsmith_organization_id: str | None = None
    langsmith_endpoint: str = "https://api.smith.langchain.com/api/v1"

    database_path: Path = Path("data/local/career_navigator.db")
    checkpoint_database_path: Path = Path("data/local/langgraph_checkpoints.db")
    run_audit_directory: Path = Path("outputs/run-audits")

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

    @field_validator("llm_provider", "market_primary_provider", "market_enrichment_provider")
    @classmethod
    def normalize_llm_provider(cls, value: str) -> str:
        """Normalize provider selection and reject an empty configured value."""

        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("LLM_PROVIDER must not be empty")
        return normalized

    @field_validator("adzuna_base_url")
    @classmethod
    def validate_adzuna_base_url(cls, value: str) -> str:
        normalized = value.strip().rstrip("/")
        if not normalized.startswith("https://") or "@" in normalized:
            raise ValueError("ADZUNA_BASE_URL must be an HTTPS URL without credentials")
        return normalized

    @field_validator("you_mcp_url")
    @classmethod
    def validate_you_mcp_url(cls, value: str) -> str:
        """Require a fixed HTTPS integration endpoint, without credentials."""

        normalized = value.strip().rstrip("/")
        if not normalized.startswith("https://"):
            raise ValueError("YOU_MCP_URL must use HTTPS")
        if "@" in normalized:
            raise ValueError("YOU_MCP_URL must not contain credentials")
        return normalized


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide immutable configuration source."""

    return Settings()
