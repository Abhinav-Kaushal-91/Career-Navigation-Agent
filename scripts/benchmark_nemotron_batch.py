"""Replay the exact ten-record GLM task once through the production NVIDIA adapter."""

import argparse
import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from benchmark_batch_role_profile import BatchRoleProfile, audit
from check_glm_evidence_contract import save

from ai_career_navigator.models import ModelGateway, ModelRole
from ai_career_navigator.models.errors import ModelGatewayError, ModelProviderError
from ai_career_navigator.models.providers import configured_provider
from ai_career_navigator.models.providers.nvidia import build_nvidia_payload
from ai_career_navigator.ui.live_workflow import load_live_settings

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "outputs/batch-role-profile/20260910T162833Z/call-01.request.json"


class Recorder:
    provider_name = "nvidia"

    def __init__(self, delegate, output):
        self.delegate, self.output = delegate, output
        self.calls = 0

    def generate_structured(self, **kwargs):
        if self.calls:
            raise ModelProviderError("One-call diagnostic budget exhausted")
        self.calls += 1
        payload = build_nvidia_payload(kwargs["request"], kwargs["model"], kwargs["output_schema"])
        save(self.output / "request.json", payload)
        start = time.monotonic()
        try:
            response = self.delegate.generate_structured(**kwargs)
        except ModelGatewayError as error:
            save(
                self.output / "failure.json",
                {"category": type(error).__name__, "seconds": round(time.monotonic() - start, 2)},
            )
            raise
        # Retain final answers only, never reasoning fields or embedded thinking blocks.
        content = response.content
        if "</think>" in content:
            content = content.rsplit("</think>", 1)[-1].strip()
        elif "<think>" in content:
            content = ""
        response = response.model_copy(update={"content": content})
        (self.output / "response.txt").write_text(content, encoding="utf-8")
        metrics = {
            "seconds": round(time.monotonic() - start, 2),
            "finish_reason": response.finish_reason,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "final_characters": len(content),
        }
        save(self.output / "metrics.json", metrics)
        print("RETURN " + json.dumps(metrics), flush=True)
        return response

    def generate_text(self, **kwargs):
        raise ModelProviderError("Text calls are outside this diagnostic")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    reference = json.loads(REFERENCE.read_text(encoding="utf-8"))
    system_prompt = reference["messages"][0]["content"]
    user_prompt = reference["messages"][1]["content"]
    assert (
        reference["response_format"]["json_schema"]["schema"]
        == BatchRoleProfile.model_json_schema()
    )
    records = json.loads(user_prompt)["postings"]
    assert len(records) == 10
    old = json.loads(
        (ROOT / "outputs/nemotron-live-overview/20260909T185859Z/results.json").read_text(
            encoding="utf-8"
        )
    )
    model = old["extraction_model"]
    assert "nemotron" in model
    settings = load_live_settings().model_copy(
        update={
            "llm_provider": "nvidia",
            "extraction_model": model,
            "reasoning_model": model,
            "model_timeout_seconds": 600,
            "model_max_output_tokens": 30000,
            "max_retries": 0,
        }
    )
    manifest = {
        "model": model,
        "records": len(records),
        "max_tokens": 30000,
        "timeout_seconds": 600,
        "max_calls": 1,
        "max_retries": 0,
        "reference_request": str(REFERENCE.relative_to(ROOT)),
        "system_sha256": hashlib.sha256(system_prompt.encode()).hexdigest(),
        "user_sha256": hashlib.sha256(user_prompt.encode()).hexdigest(),
        "provider_differences": (
            "NVIDIA JSON-object mode with schema in system message; "
            "enable_thinking=false; non-streaming."
        ),
        "production_settings_changed": False,
        "nvidia_key_present": settings.nvidia_api_key is not None,
    }
    if not args.live:
        print(json.dumps(manifest, indent=2))
        return
    if settings.nvidia_api_key is None:
        raise ValueError("NVIDIA key missing; no request sent")
    output = ROOT / "outputs/nemotron-batch-profile" / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output.mkdir(parents=True, exist_ok=False)
    save(output / "manifest.json", manifest)
    print(f"OUTPUT {output}", flush=True)
    print("START " + model, flush=True)
    recorder = Recorder(configured_provider(settings), output)
    gateway = ModelGateway.from_settings(settings, providers={"nvidia": recorder})
    try:
        response = gateway.generate_structured(
            role=ModelRole.EXTRACTION,
            output_schema=BatchRoleProfile,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
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
