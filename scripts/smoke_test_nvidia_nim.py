"""Manual-only NVIDIA NIM text and structured-output smoke validation."""

import argparse
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from ai_career_navigator.config import Settings
from ai_career_navigator.models import ModelGateway, ModelRole


class SmokePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env"),
        help="Local environment file read through Settings; secret values are never printed.",
    )
    args = parser.parse_args()
    settings = Settings(_env_file=args.env_file)
    if settings.llm_provider != "nvidia":
        raise SystemExit("Set LLM_PROVIDER=nvidia before running this manual smoke test.")
    if settings.nvidia_api_key is None:
        raise SystemExit("NVIDIA_API_KEY is required. The key will not be printed.")

    gateway = ModelGateway.from_settings(settings)
    structured = gateway.generate_structured(
        role=ModelRole.EXTRACTION,
        output_schema=SmokePayload,
        system_prompt="Return only valid JSON matching the requested schema.",
        user_prompt='Return exactly this JSON object: {"status":"ready"}',
        temperature=0,
        max_tokens=32,
        metadata={"task_type": "manual_nvidia_structured_smoke"},
    )
    reasoning = gateway.generate_text(
        role=ModelRole.REASONING,
        system_prompt="Return only the concise final answer without a reasoning trace.",
        user_prompt="Reply with exactly: NVIDIA NIM ready",
        temperature=0,
        max_tokens=64,
        metadata={"task_type": "manual_nvidia_reasoning_smoke"},
    )
    validated = SmokePayload.model_validate(structured.structured_output)
    print(
        f"structured_provider={structured.provider} model={structured.model} "
        f"status={validated.status} latency_ms={structured.latency_ms:.0f} "
        f"input_tokens={structured.input_tokens} output_tokens={structured.output_tokens}"
    )
    print(
        f"reasoning_provider={reasoning.provider} model={reasoning.model} "
        f"latency_ms={reasoning.latency_ms:.0f} input_tokens={reasoning.input_tokens} "
        f"output_tokens={reasoning.output_tokens} response={reasoning.content[:80]!r}"
    )


if __name__ == "__main__":
    main()
