"""One explicitly authorized synthetic CURRENT-A run through the website runtime.

Exports contain only the synthetic test profile and public posting data. They stay
local; delete outputs/v1-reliability-20260906/live-* after the review if unwanted.
No expected outcomes, frozen postings, or recorded model responses enter this run.
"""

import argparse
import asyncio
import json
import os
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

from pydantic_core import to_jsonable_python

from ai_career_navigator.config import Settings
from ai_career_navigator.evaluation.v1_replay import build_inputs, replay_cases
from ai_career_navigator.models.errors import ModelGatewayError
from ai_career_navigator.models.inspection import LocalModelInspector
from ai_career_navigator.models.protocols import ModelProvider
from ai_career_navigator.models.providers import configured_provider
from ai_career_navigator.ui.live_workflow import build_live_workflow_runtime, load_live_settings

DEFAULT_OUTPUT = Path("outputs/v1-reliability-20260906/live-current-a.json")


class LiveModelBudgetExceeded(ModelGatewayError):
    """A non-retryable local budget stop, distinct from provider failure."""


class BudgetModelProvider:
    """Wrap the public provider protocol and count every actual provider invocation."""

    def __init__(
        self,
        provider: ModelProvider,
        *,
        max_calls: int = 30,
        deadline_seconds: float = 600,
        clock=time.monotonic,
    ):
        self.provider = provider
        self.max_calls = max_calls
        self.calls = 0
        self.clock = clock
        self.deadline = clock() + deadline_seconds
        self.stops = 0
        self.lock = Lock()

    @property
    def provider_name(self):
        return self.provider.provider_name

    def _timeout(self, requested):
        with self.lock:
            remaining = self.deadline - self.clock()
            if self.calls >= self.max_calls or remaining <= 0:
                self.stops += 1
                raise LiveModelBudgetExceeded(
                    "Synthetic live run reached its model-call or time budget."
                )
            self.calls += 1
            return min(float(requested), 60.0, remaining)

    def generate_text(self, *, request, model, timeout_seconds):
        return self.provider.generate_text(
            request=request, model=model, timeout_seconds=self._timeout(timeout_seconds)
        )

    def generate_structured(self, *, request, model, output_schema, timeout_seconds):
        return self.provider.generate_structured(
            request=request,
            model=model,
            output_schema=output_schema,
            timeout_seconds=self._timeout(timeout_seconds),
        )


def bounded_settings(base: Settings, output: Path) -> tuple[Settings, dict[str, Any]]:
    overrides = {
        "market_analysis_posting_limit": 5,
        "market_max_total_search_calls": 6,
        "market_max_content_fetches": 12,
        "max_retries": 1,
        "model_timeout_seconds": min(base.model_timeout_seconds, 60),
        "market_timeout_seconds": min(base.market_timeout_seconds, 30),
        "langsmith_tracing": False,
        "model_inspector_enabled": True,
        "run_audit_directory": output.parent / "live-run-audits",
    }
    settings = base.model_copy(update=overrides)
    return settings, {
        key: {"production": str(getattr(base, key)), "live_validation": str(value)}
        for key, value in overrides.items()
        if getattr(base, key) != value
    }


def synthetic_inputs():
    # build_inputs reads only factual candidate/goal fields, never the evaluator rubric,
    # posting expectations, frozen market clients, or model recordings.
    case = next(case for case in replay_cases() if case.case_id == "CURRENT-A")
    return build_inputs(case)


async def run_once(output: Path) -> dict[str, Any]:
    # Explicitly disable LangChain/LangSmith environment tracing as well as app Settings.
    os.environ["LANGSMITH_TRACING"] = "false"
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    base = load_live_settings()
    settings, overrides = bounded_settings(base, output)
    if settings.llm_provider != "nvidia":
        raise ValueError("This validation requires the website's configured NVIDIA provider.")
    budget = BudgetModelProvider(configured_provider(settings))
    runtime = build_live_workflow_runtime(settings, provider_override=budget)
    profile, goal = synthetic_inputs()
    run_id = uuid4()
    thread_id = f"synthetic-live-current-a-{run_id}"
    started_at = datetime.now(UTC)
    stages = []
    failure = None
    state = {}
    started = time.monotonic()
    try:
        async with asyncio.timeout(600):
            async for stage in runtime.controller.stream_start(
                thread_id=thread_id,
                confirmed_profile=profile,
                confirmed_goal=goal,
                capability_inference_requested=False,
                run_id=run_id,
            ):
                stages.append(
                    {"stage": stage, "elapsed_seconds": round(time.monotonic() - started, 2)}
                )
                print(f"Completed stage: {stage}", flush=True)
    except Exception as error:
        failure = {"category": type(error).__name__, "detail": str(error)}
        print(f"Run stopped: {type(error).__name__}", flush=True)
    finally:
        try:
            state = runtime.controller.inspect(thread_id=thread_id).state
        except Exception as error:
            failure = failure or {
                "category": type(error).__name__,
                "detail": "Partial graph state unavailable.",
            }
    serial = to_jsonable_python(state)
    synthesis = serial.get("career_assessment_synthesis") or {}
    snapshot = serial.get("market_snapshot") or {}
    artifact = {
        "mode": "LIVE_PRODUCTION_RUNTIME_WITH_DISCLOSED_BOUNDS",
        "synthetic_profile": True,
        "case_id": "CURRENT-A",
        "run_id": str(run_id),
        "thread_id": thread_id,
        "started_at": started_at.isoformat(),
        "finished_at": datetime.now(UTC).isoformat(),
        "elapsed_seconds": round(time.monotonic() - started, 2),
        "settings_overrides": overrides,
        "effective_settings": {
            name: getattr(settings, name)
            for name in (
                "llm_provider",
                "extraction_model",
                "reasoning_model",
                "validation_model",
                "market_analysis_posting_limit",
                "market_max_total_search_calls",
                "market_max_content_fetches",
                "market_max_enrichments",
                "market_target_posting_count",
                "market_max_posting_age_days",
                "model_timeout_seconds",
                "market_timeout_seconds",
                "max_retries",
                "langsmith_tracing",
                "model_inspector_enabled",
            )
        },
        "limits": {
            "model_provider_invocations": 30,
            "model_deadline_seconds": 600,
            "whole_run_deadline_seconds": 600,
        },
        "model_usage": asdict(runtime.model_usage),
        "actual_model_provider_invocations": budget.calls,
        "budget_stops": budget.stops,
        "progress": stages,
        "failure": failure,
        "actual_stage": serial.get("current_stage"),
        "actual_workflow_status": serial.get("workflow_status"),
        "actual_accessibility": synthesis.get("accessibility"),
        "validated_postings": snapshot.get("validated_posting_count"),
        "graph_state": serial,
        "model_inspector_events": runtime.model_gateway.inspector.events
        if runtime.model_gateway.inspector
        else [],
        "retention": (
            "Local synthetic/profile and public-source audit. Delete live artifacts after review "
            "if unwanted. No external telemetry."
        ),
        "interpretation": (
            "Live observations only. An empty or changed market is not scored against frozen "
            "vacancy counts or forced accessibility labels."
        ),
    }
    secrets = tuple(
        value.get_secret_value()
        for name in type(settings).model_fields
        if hasattr((value := getattr(settings, name)), "get_secret_value")
    )
    sanitizer = LocalModelInspector(secrets=secrets, max_events=1)
    sanitizer.record("live_run_artifact", artifact=artifact)
    artifact = sanitizer.events[0]["artifact"]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Saved live artifact: {output.resolve()}", flush=True)
    print(
        f"Outcome: {artifact['actual_stage']} / {artifact['actual_accessibility']} / "
        f"{artifact['validated_postings']} postings",
        flush=True,
    )
    return artifact


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-live",
        action="store_true",
        help="Permit one synthetic CURRENT-A call sequence to configured live providers.",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    if not args.allow_live:
        parser.error("No provider calls made: --allow-live is required.")
    asyncio.run(run_once(args.output))


if __name__ == "__main__":
    main()
