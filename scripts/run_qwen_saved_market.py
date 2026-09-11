"""Bounded streaming HF diagnostic over the frozen 28-posting demo corpus."""

import argparse
import json
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import httpx
from compare_saved_extractions import SAVED_RUN, PostingCandidateAssessment
from huggingface_hub import InferenceClient
from pydantic_core import to_jsonable_python

from ai_career_navigator.config import Settings
from ai_career_navigator.domain import CandidateProfile, CareerGoal, CurrentMarketSnapshot
from ai_career_navigator.market import MarketPostingEvidence, analyze_market_requirements
from ai_career_navigator.market.requirements import extract_posting_requirements
from ai_career_navigator.models import ModelGateway, ModelRole
from ai_career_navigator.models.errors import ModelProviderError
from ai_career_navigator.models.providers.nvidia import build_nvidia_payload
from ai_career_navigator.models.schemas import ModelResponse
from ai_career_navigator.orchestration import (
    TransientMarketContentStore,
    WorkflowRuntimeContext,
    nodes,
    routing,
)
from ai_career_navigator.profile.inference import infer_capabilities

ROOT = Path(__file__).resolve().parents[1]
MODEL = "Qwen/Qwen3.8-27B"


class DiagnosticSettings(Settings):
    fireworks_model: str = ""


class FireworksStreamClient:
    """Direct Fireworks SSE transport; no HF routing and no SDK auto-retries."""

    def __init__(self, *, api_key, timeout):
        self.key = api_key
        self.timeout = timeout

    def chat_completion(self, **payload):
        payload.update(payload.pop("extra_body", {}))
        with httpx.Client(timeout=self.timeout) as client:
            with client.stream(
                "POST",
                "https://api.fireworks.ai/inference/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.key}"},
                json=payload,
            ) as response:
                if response.is_error:
                    # Caller redacts the configured secret before saving this message.
                    raise RuntimeError(
                        f"HTTP {response.status_code}: {response.read().decode()[:1200]}"
                    )
                for line in response.iter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        return
                    item = json.loads(data)
                    if "error" in item:
                        raise RuntimeError("Provider returned an in-stream error")
                    usage = item.get("usage")
                    yield SimpleNamespace(
                        usage=SimpleNamespace(**usage) if usage else None,
                        choices=[
                            SimpleNamespace(
                                delta=SimpleNamespace(content=c.get("delta", {}).get("content")),
                                finish_reason=c.get("finish_reason"),
                            )
                            for c in item.get("choices", [])
                        ],
                    )


class StreamingDiagnosticProvider:
    provider_name = "hf-diagnostic"
    thinking_requested = False

    def __init__(self, secret, output):
        self.secret = secret.get_secret_value()
        self.output = output
        self.calls = 0
        self.failures = 0
        self.deadline = time.monotonic() + 1800

    def client(self, **kwargs):
        return InferenceClient(**kwargs)

    def generate_structured(self, *, request, model, output_schema, timeout_seconds):
        if self.calls >= 45 or time.monotonic() >= self.deadline or self.failures >= 2:
            raise ModelProviderError("Diagnostic budget/circuit breaker reached; call not sent")
        self.calls += 1
        call = self.output / f"call-{self.calls:02d}"
        call.mkdir()
        payload = build_nvidia_payload(request, model, output_schema)
        payload["messages"] = [
            {
                "role": "system",
                "content": "\n\n".join(
                    m["content"] for m in payload["messages"] if m["role"] == "system"
                ),
            },
            *[m for m in payload["messages"] if m["role"] != "system"],
        ]
        payload["extra_body"] = {"chat_template_kwargs": payload.pop("chat_template_kwargs")}
        payload["extra_body"]["chat_template_kwargs"]["enable_thinking"] = self.thinking_requested
        payload.update(stream=True, max_tokens=20000, stream_options={"include_usage": True})
        (call / "request.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"CALL {self.calls} START {request.response_schema_name}", flush=True)
        start = time.monotonic()
        text = ""
        finish = None
        usage = None
        first = None
        try:
            client = self.client(
                api_key=self.secret, timeout=min(timeout_seconds, self.deadline - time.monotonic())
            )
            for chunk in client.chat_completion(**payload):
                if time.monotonic() >= min(self.deadline, start + 600):
                    raise TimeoutError("Diagnostic streaming wall-clock deadline reached")
                if first is None:
                    first = time.monotonic() - start
                    print(f"CALL {self.calls} FIRST CHUNK {first:.2f}s", flush=True)
                if chunk.usage is not None:
                    usage = chunk.usage
                for choice in chunk.choices:
                    # Deliberately never read or save reasoning_content fields.
                    text += choice.delta.content or ""
                    finish = choice.finish_reason or finish
            if "</think>" in text:
                text = text.rsplit("</think>", 1)[-1].strip()
            elif "<think>" in text:
                text = ""
            elapsed = time.monotonic() - start
            metrics = {
                "elapsed_seconds": elapsed,
                "first_chunk_seconds": first,
                "finish_reason": finish,
                "input_tokens": getattr(usage, "prompt_tokens", None),
                "output_tokens": getattr(usage, "completion_tokens", None),
                "final_characters": len(text),
                "status": "RETURNED",
                "thinking_requested": self.thinking_requested,
                "thinking_honored": "not independently verified",
            }
            (call / "response.txt").write_text(text, encoding="utf-8")
            (call / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
            print(f"CALL {self.calls} RETURN {json.dumps(metrics)}", flush=True)
            return ModelResponse(
                content=text,
                provider=self.provider_name,
                model=model,
                role=request.role,
                finish_reason=finish,
                latency_ms=elapsed * 1000,
                input_tokens=metrics["input_tokens"],
                output_tokens=metrics["output_tokens"],
            )
        except Exception as exc:
            self.failures += 1
            message = re.sub(
                r"hf_[A-Za-z0-9]+", "[REDACTED]", str(exc).replace(self.secret, "[REDACTED]")
            )
            failure = {
                "status": "FAILED",
                "category": type(exc).__name__,
                "elapsed_seconds": time.monotonic() - start,
                "first_chunk_seconds": first,
                "sanitized_message": message[:1500],
            }
            (call / "failure.json").write_text(json.dumps(failure, indent=2), encoding="utf-8")
            print(f"CALL {self.calls} FAILED {json.dumps(failure)}", flush=True)
            raise ModelProviderError("Streaming request failed; see sanitized artifact") from None


class FireworksStreamingDiagnosticProvider(StreamingDiagnosticProvider):
    provider_name = "fireworks-diagnostic"
    thinking_requested = True

    def client(self, **kwargs):
        return FireworksStreamClient(**kwargs)


def all_postings(sources, **kwargs):
    # User-authorized diagnostic bound only; production's limit remains unchanged.
    kwargs["posting_limit"] = 28
    return analyze_market_requirements(sources, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--fireworks", action="store_true")
    args = parser.parse_args()
    saved = json.loads(
        (ROOT / "outputs/demo-profile-live/20260909T194458Z/results.json").read_text()
    )
    evidence = [MarketPostingEvidence.model_validate(x) for x in saved["retained_posting_evidence"]]
    assert len(evidence) == 28
    profile = CandidateProfile.model_validate(saved["confirmed_profile"])
    goal = CareerGoal.model_validate(saved["goal"])
    if not args.live:
        print("Dry run: 28 saved postings; synthetic confirmed profile; no network calls.")
        return
    settings = DiagnosticSettings(_env_file=ROOT / "src/ai_career_navigator/.env")
    secret = settings.fireworks_api_key if args.fireworks else settings.hf_token
    model = settings.fireworks_model if args.fireworks else MODEL
    if secret is None or not model:
        raise SystemExit("Requested provider key/model missing; no calls made")
    if args.fireworks and not model.startswith("accounts/fireworks/models/glm-"):
        raise SystemExit("Expected configured Fireworks GLM model; no calls made")
    folder = "fireworks-saved-market" if args.fireworks else "qwen-saved-market"
    output = ROOT / "outputs" / folder / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output.mkdir(parents=True, exist_ok=False)
    print(f"ARTIFACTS {output}", flush=True)
    provider_class = (
        FireworksStreamingDiagnosticProvider if args.fireworks else StreamingDiagnosticProvider
    )
    provider = provider_class(secret, output)
    gateway = ModelGateway(
        provider=provider, models={r: model for r in ModelRole}, timeout_seconds=600, max_retries=0
    )
    report = {
        "mode": "LIVE_FROZEN_28_POSTING_DIAGNOSTIC",
        "provider": provider.provider_name,
        "model": model,
        "nodes": [],
        "scope": {
            "max_calls": 45,
            "deadline_seconds": 1800,
            "max_tokens": 20000,
            "fresh_retrieval": False,
            "production_provider_changed": False,
            "inferred_strengths_auto_approved": False,
            "plan_auto_approved": False,
        },
    }

    def save():
        report["actual_calls"] = provider.calls
        (output / "results.json").write_text(
            json.dumps(to_jsonable_python(report), indent=2), encoding="utf-8"
        )

    save()
    # First prove long-form streaming transport before spending on the 28-item workflow.
    probe_saved = json.loads(SAVED_RUN.read_text(encoding="utf-8"))
    probe = PostingCandidateAssessment.model_validate(probe_saved["postings"][0]["assessment"])
    report["full_description_probe"] = extract_posting_requirements(probe, gateway)
    save()
    if provider.failures:
        report["stop_reason"] = "STREAMING_PROBE_FAILED; 28-posting calls not sent"
        save()
        return
    store = TransientMarketContentStore()
    context = WorkflowRuntimeContext(
        settings=settings,
        model_gateway=gateway,
        market_client_factory=lambda: None,
        content_store=store,
        market_processing_service=all_postings,
    )
    runtime = SimpleNamespace(context=context)
    state = {
        "run_id": uuid4(),
        "confirmed_profile": profile,
        "confirmed_goal": goal,
        "market_snapshot": CurrentMarketSnapshot.model_validate(
            saved["graph_state"]["market_snapshot"]
        ),
    }
    state.update(nodes.initialize_run(state, runtime))
    state["market_source_ids"] = store.put_posting_evidence(state["run_id"], evidence)
    report["ai_strength_review"] = infer_capabilities(profile, gateway)
    report["state"] = state
    save()

    def step(name):
        state.update(getattr(nodes, name)(state, runtime))
        report["nodes"].append(name)
        report["market_analysis"] = store.get_analysis(state["run_id"])
        save()
        print(f"NODE {name} STATUS {state['workflow_status']}", flush=True)

    try:
        step("market_processing")
        if routing.route_after_market_processing(state) == "end":
            return
        step("market_ready")
        if routing.route_after_market_ready(state) == "end":
            return
        step("candidate_requirement_comparison")
        if routing.route_after_candidate_comparison(state) == "end":
            return
        step("gap_and_accessibility_analysis")
        step("career_assessment_synthesis")
        if routing.route_after_candidate_assessment(state) == "bridge":
            step("bridge_role_assessment")
        step("timeline_assessment")
        step("career_plan_generation")
        # Stop for human review: never auto-approve a generated plan.
    except Exception as exc:
        report["failure_category"] = type(exc).__name__
    finally:
        report["finished_at"] = datetime.now(UTC)
        save()


if __name__ == "__main__":
    main()
