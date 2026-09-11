"""One tiny no-retry capability probe; retain only sanitized API error details."""

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx

from ai_career_navigator.models import ModelGateway, ModelRole
from ai_career_navigator.models.errors import ModelGatewayError
from ai_career_navigator.models.inspection import LocalModelInspector
from ai_career_navigator.models.providers.fireworks import (
    FIREWORKS_CHAT_COMPLETIONS_URL,
    FireworksProvider,
)
from ai_career_navigator.ui.live_workflow import load_live_settings


class Probe(FireworksProvider):
    def _stream_response(self, payload, request, model, timeout_seconds):
        payload = {**payload, "reasoning_effort": "none", "stream": False}
        payload.pop("stream_options", None)
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.post(
                FIREWORKS_CHAT_COMPLETIONS_URL,
                headers={"Authorization": "Bearer " + self._api_key},
                json=payload,
            )
        details = {
            "http_status": response.status_code,
            "reasoning_effort": "none",
            "max_tokens": payload["max_tokens"],
            "model": model,
        }
        if response.is_error:
            inspector = LocalModelInspector(secrets=(self._api_key,))
            try:
                error = response.json().get("error", {})
                message = error.get("message", "") if isinstance(error, dict) else str(error)
            except ValueError:
                message = "Non-JSON error response (body not retained)"
            inspector.record("provider_error", message=str(message)[:1500])
            details["error"] = inspector.events
        folder = Path(__file__).resolve().parents[1] / "outputs/glm-reasoning-control"
        path = folder / (
            "capability-probe-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + ".json"
        )
        path.write_text(json.dumps(details, indent=2), encoding="utf-8")
        print(json.dumps(details), flush=True)
        if response.is_error:
            self._raise_http_error(response.status_code)
        return self._normalize(
            response.content, request=request, requested_model=model, latency_ms=0
        )


if __name__ == "__main__":
    settings = load_live_settings().model_copy(
        update={
            "model_timeout_seconds": 20,
            "model_max_output_tokens": 32,
            "max_retries": 0,
        }
    )
    gateway = ModelGateway.from_settings(
        settings, providers={"fireworks": Probe(settings.fireworks_api_key, streaming=True)}
    )
    try:
        gateway.generate_text(
            role=ModelRole.EXTRACTION,
            system_prompt="Reply briefly.",
            user_prompt="Reply OK.",
            max_tokens=32,
        )
    except ModelGatewayError as error:
        print(type(error).__name__)
