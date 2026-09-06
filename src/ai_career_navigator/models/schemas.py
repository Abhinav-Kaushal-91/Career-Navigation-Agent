"""Provider-neutral model request and response schemas."""

from typing import Any, TypeAlias

from pydantic import BaseModel, ConfigDict, Field

from ai_career_navigator.models.enums import ModelRole

MetadataValue: TypeAlias = str | int | float | bool | None


class ModelRequest(BaseModel):
    """A model call without provider credentials or provider-specific options."""

    model_config = ConfigDict(frozen=True)

    role: ModelRole
    system_prompt: str = ""
    user_prompt: str = Field(min_length=1)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, gt=0)
    response_schema_name: str | None = None
    metadata: dict[str, MetadataValue] = Field(default_factory=dict)


class ModelResponse(BaseModel):
    """Normalized response returned by every provider adapter."""

    model_config = ConfigDict(frozen=True)

    content: str
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    role: ModelRole
    finish_reason: str | None = None
    latency_ms: float = Field(ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    request_id: str | None = None
    structured_output: dict[str, Any] | None = None
    warnings: list[str] = Field(default_factory=list)
