"""One-variable replay of the saved five-JD request with explicit reasoning effort."""

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from benchmark_batch_role_profile import BatchRoleProfile, audit
from check_glm_evidence_contract import save

from ai_career_navigator.models import ModelGateway, ModelRole
from ai_career_navigator.models.errors import ModelGatewayError, ModelProviderError
from ai_career_navigator.models.providers.fireworks import FireworksProvider
from ai_career_navigator.ui.live_workflow import load_live_settings

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "outputs/batch-role-profile/20260910T164628Z/call-01.request.json"


class ControlledProvider(FireworksProvider):
    def __init__(self, api_key, output, reference, effort="none"):
        super().__init__(api_key, streaming=True)
        self.output, self.reference = output, reference
        self.calls = 0
        self.effort = effort

    def _stream_response(self, payload, request, model, timeout_seconds):
        if self.calls:
            raise ModelProviderError("Diagnostic limited to one provider call")
        # Verify the entire wire body before adding the one experimental setting.
        if payload != self.reference:
            raise ModelProviderError("Request differs from control; not sent")
        self.calls += 1
        payload = {**payload, "reasoning_effort": self.effort}
        save(self.output / "request.json", payload)
        started = time.monotonic()
        try:
            response = super()._stream_response(payload, request, model, timeout_seconds)
        except ModelGatewayError as error:
            save(
                self.output / "failure.json",
                {"category": type(error).__name__, "seconds": round(time.monotonic() - started, 2)},
            )
            raise
        (self.output / "response.txt").write_text(response.content, encoding="utf-8")
        metrics = {
            "seconds": round(time.monotonic() - started, 2),
            "finish_reason": response.finish_reason,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "final_characters": len(response.content),
        }
        save(self.output / "metrics.json", metrics)
        print("RETURN " + json.dumps(metrics), flush=True)
        return response


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--effort", choices=["none", "high"], default="none")
    args = parser.parse_args()
    reference = json.loads(REFERENCE.read_text(encoding="utf-8"))
    assert (
        reference["response_format"]["json_schema"]["schema"]
        == BatchRoleProfile.model_json_schema()
    )
    records = json.loads(reference["messages"][-1]["content"])["postings"]
    assert len(records) == 5
    if not args.live:
        print(
            f"Five saved descriptions; reasoning_effort={args.effort}; no API call."
        )
        return
    settings = load_live_settings().model_copy(update={"max_retries": 0})
    if settings.llm_provider != "fireworks" or settings.extraction_model != reference["model"]:
        raise ValueError("Configured model changed; refusing uncontrolled comparison")
    output = ROOT / "outputs/glm-reasoning-control" / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output.mkdir(parents=True, exist_ok=False)
    save(
        output / "manifest.json",
        {
            "reference": str(REFERENCE.relative_to(ROOT)),
            "records": 5,
            "model": settings.extraction_model,
            "sole_wire_change": {"reasoning_effort": args.effort},
            "max_calls": 1,
            "max_retries": 0,
            "timeout_seconds": settings.model_timeout_seconds,
            "production_changed": False,
            "documentation": "https://docs.fireworks.ai/api-reference/post-chatcompletions",
            "compatibility_note": (
                "GLM 5.3 Flash not explicitly in reasoning support table; "
                "live test verifies acceptance."
            ),
        },
    )
    provider = ControlledProvider(settings.fireworks_api_key, output, reference, args.effort)
    gateway = ModelGateway.from_settings(settings, providers={"fireworks": provider})
    print(f"OUTPUT {output}", flush=True)
    print(f"START reasoning_effort={args.effort}; otherwise identical five-JD request", flush=True)
    try:
        response = gateway.generate_structured(
            role=ModelRole.EXTRACTION,
            output_schema=BatchRoleProfile,
            system_prompt=reference["messages"][0]["content"],
            user_prompt=reference["messages"][-1]["content"],
            temperature=reference["temperature"],
            max_tokens=reference["max_tokens"],
        )
        result = BatchRoleProfile.model_validate(response.structured_output)
        save(output / "structured.json", result.model_dump())
        checked = audit(result, records)
        save(output / "audit.json", checked)
        print(
            "AUDIT " + json.dumps({k: v for k, v in checked.items() if k != "themes"}), flush=True
        )
    except ModelGatewayError as error:
        save(output / "validation_failure.json", {"category": type(error).__name__})
        print("FAILED " + type(error).__name__, flush=True)


if __name__ == "__main__":
    main()
