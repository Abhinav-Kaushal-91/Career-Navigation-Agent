"""Run the production demo-to-analysis backend, without browser or session mutations."""

import argparse
import asyncio
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from uuid import uuid4

from pydantic_core import to_jsonable_python

from ai_career_navigator.domain import ApprovalStatus, CareerGoal, GeographyScope, GoalType
from ai_career_navigator.models import ModelGatewayError
from ai_career_navigator.models.inspection import LocalModelInspector
from ai_career_navigator.models.providers import configured_provider
from ai_career_navigator.profile.inference import infer_capabilities
from ai_career_navigator.profile.service import build_candidate_profile
from ai_career_navigator.ui.demo_data import sample_profile_draft
from ai_career_navigator.ui.live_workflow import build_live_workflow_runtime, load_live_settings


class BoundedRecorder:
    def __init__(self, delegate, output, sanitizer, *, max_calls=40):
        self.delegate = delegate
        self.provider_name = delegate.provider_name
        self.output = output
        self.sanitizer = sanitizer
        self.calls = 0
        self.max_calls = max_calls
        self.lock = Lock()
        self.deadline = time.monotonic() + 1800

    def generate_structured(self, **kwargs):
        with self.lock:
            if self.calls >= self.max_calls or time.monotonic() >= self.deadline:
                raise ModelGatewayError("Diagnostic call/time budget exhausted")
            self.calls += 1
            index = self.calls
        kwargs["timeout_seconds"] = min(kwargs["timeout_seconds"], self.deadline - time.monotonic())
        request = kwargs["request"]
        task = request.metadata.get("task_type", request.response_schema_name)
        record = {"index": index, "task": task, "request": request.model_dump(mode="json")}
        started = time.monotonic()
        print(f"MODEL {index} START {task}", flush=True)
        try:
            response = self.delegate.generate_structured(**kwargs)
            record["response"] = response.model_dump(mode="json")
            return response
        except Exception as error:
            record["error_category"] = type(error).__name__
            raise
        finally:
            record["seconds"] = round(time.monotonic() - started, 2)
            with self.lock:
                self.sanitizer.record("model_call", **record)
                (self.output / f"model-{index:02d}.json").write_text(
                    json.dumps(self.sanitizer.events[-1], indent=2), encoding="utf-8"
                )
            print(
                f"MODEL {index} END {record['seconds']}s "
                f"{record.get('error_category', 'RETURNED')}",
                flush=True,
            )

    def generate_text(self, **kwargs):
        raise ModelGatewayError("Unstructured calls are outside this diagnostic")


async def run(live):
    base = load_live_settings()
    draft = sample_profile_draft()
    profile = build_candidate_profile(draft, approved=True)
    print(
        f"SYNTHETIC DEMO: {profile.current_role}; Education entries: {len(draft.education)}",
        flush=True,
    )
    print(f"Provider: {base.llm_provider}; model: {base.extraction_model}; live={live}", flush=True)
    if not live:
        return
    os.environ["LANGSMITH_TRACING"] = "false"
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    output = Path("outputs/demo-to-analysis") / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output.mkdir(parents=True, exist_ok=False)
    settings = base.model_copy(
        update={
            "langsmith_tracing": False,
            "run_audit_directory": output / "run-audits",
        }
    )
    secrets = tuple(
        value.get_secret_value()
        for name in type(settings).model_fields
        if hasattr((value := getattr(settings, name)), "get_secret_value")
    )
    sanitizer = LocalModelInspector(secrets=secrets, max_events=1)
    recorder = BoundedRecorder(configured_provider(settings), output, sanitizer)
    runtime = build_live_workflow_runtime(settings, provider_override=recorder)
    run_id = uuid4()
    thread_id = f"backend-analysis-{run_id}"
    report = {
        "mode": "FRESH_LIVE_BACKEND_SYNTHETIC_DEMO_TO_ANALYSIS",
        "run_id": str(run_id),
        "profile_draft": draft,
        "confirmed_profile": profile,
        "provider": settings.llm_provider,
        "model": settings.extraction_model,
        "max_output_tokens": settings.model_max_output_tokens,
        "inferred_strengths_auto_approved": False,
        "browser_used": False,
        "production_session_changed": False,
        "steps": [],
    }

    def save():
        with recorder.lock:
            sanitizer.record("report", data=to_jsonable_python(report))
            (output / "results.json").write_text(
                json.dumps(sanitizer.events[-1]["data"], indent=2), encoding="utf-8"
            )

    started = time.monotonic()
    print(f"OUTPUT {output.resolve()}", flush=True)
    save()
    try:
        inference = await asyncio.to_thread(infer_capabilities, profile, runtime.model_gateway)
        report["ai_strength_review"] = inference
        elapsed = round(time.monotonic() - started, 2)
        report["steps"].append(
            {"step": "ai_strength_review", "seconds": elapsed, "status": inference.status}
        )
        print(f"STRENGTH REVIEW {inference.status} {elapsed}s", flush=True)
        report["goal"] = goal = CareerGoal(
            goal_type=GoalType.CURRENT_MARKET_ANALYSIS,
            target_role="Senior Java Developer",
            target_location="Toronto, Canada",
            geography_scopes=[GeographyScope.METRO_AREA],
            target_timeline_months=None,
            search_expansion_permission=True,
            approval_status=ApprovalStatus.APPROVED,
            approved_at=datetime.now(UTC),
        )
        save()
        previous = time.monotonic()
        async with asyncio.timeout(max(1, recorder.deadline - time.monotonic())):
            async for node in runtime.controller.stream_start(
                thread_id=thread_id,
                confirmed_profile=profile,
                confirmed_goal=goal,
                capability_inference_requested=False,
                run_id=run_id,
            ):
                now = time.monotonic()
                report["steps"].append({"step": node, "seconds": round(now - previous, 2)})
                previous = now
                report["graph_state"] = runtime.controller.inspect(thread_id=thread_id).state
                print(f"STEP {node}: {report['steps'][-1]['seconds']}s", flush=True)
                save()
                if node == "career_assessment_synthesis":
                    break  # Requested endpoint: analysis, not Plan generation/approval.
    except Exception as error:
        report["exception_category"] = type(error).__name__
    finally:
        state = runtime.controller.inspect(thread_id=thread_id).state
        report["graph_state"] = state
        store = runtime.controller._context.content_store
        report["retained_posting_evidence"] = store.get_posting_evidence(run_id)
        report["market_analysis"] = store.get_analysis(run_id)
        report["total_seconds"] = round(time.monotonic() - started, 2)
        report["model_calls"] = recorder.calls
        report["analysis_node_reached"] = any(
            row["step"] == "career_assessment_synthesis" for row in report["steps"]
        )
        save()
        print(f"FINISHED {output.resolve() / 'results.json'}", flush=True)
        print(
            json.dumps(
                {
                    key: report[key]
                    for key in ["total_seconds", "model_calls", "analysis_node_reached", "steps"]
                },
                default=str,
            ),
            flush=True,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    asyncio.run(run(parser.parse_args().live))
