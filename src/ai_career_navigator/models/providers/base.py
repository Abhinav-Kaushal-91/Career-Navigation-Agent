"""Small implementation base shared by concrete provider adapters."""

from abc import ABC, abstractmethod
from typing import Any

from ai_career_navigator.models.schemas import ModelRequest, ModelResponse


class BaseModelProvider(ABC):
    """Give adapters a safe representation and a consistent implementation shape."""

    provider_name: str

    def __repr__(self) -> str:
        return f"<{type(self).__name__} provider_name={self.provider_name!r}>"

    @abstractmethod
    def generate_text(
        self, *, request: ModelRequest, model: str, timeout_seconds: float
    ) -> ModelResponse:
        """Generate a normalized text response."""

    @abstractmethod
    def generate_structured(
        self,
        *,
        request: ModelRequest,
        model: str,
        output_schema: dict[str, Any],
        timeout_seconds: float,
    ) -> ModelResponse:
        """Generate normalized content constrained by a JSON schema."""
