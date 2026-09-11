"""One isolated live demo-profile workflow; no production/session mutation."""

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
from test_saved_nemotron_overview import DiagnosticGateway, DiagnosticNvidiaProvider

from ai_career_navigator.domain import ApprovalStatus, CareerGoal, GeographyScope, GoalType
from ai_career_navigator.market import build_enrichment_market_client, build_primary_market_client
from ai_career_navigator.models import ModelGatewayError
from ai_career_navigator.models.inspection import LocalModelInspector
from ai_career_navigator.orchestration import (
    CareerWorkflowController,
    TransientMarketContentStore,
    WorkflowRuntimeContext,
    build_career_graph,
)
from ai_career_navigator.profile.inference import infer_capabilities
from ai_career_navigator.profile.service import build_candidate_profile
from ai_career_navigator.ui.demo_data import sample_profile_draft
from ai_career_navigator.ui.live_workflow import load_live_settings
from ai_career_navigator.ui.view_models import (
    analysis_view_model,
    market_view_model,
    plan_view_model,
)


class DiagnosticBudgetExceeded(ModelGatewayError):
    """Non-retryable diagnostic bound, not missing market/candidate evidence."""


class PersistedInspector(LocalModelInspector):
    def __init__(self, path, *, secrets):
        super().__init__(secrets=secrets, max_events=1000)
        self.path = path
        self.lock = Lock()

    def record(self, event, **fields):
        with self.lock:
            super().record(event, **fields)
            self.path.write_text(json.dumps(self.events, indent=2), encoding="utf-8")


class BoundedProvider(DiagnosticNvidiaProvider):
    def __init__(self, key):
        super().__init__(key)
        self.calls = 0
        self.deadline = time.monotonic() + 1800

    def generate_structured(self, **kwargs):
        remaining = self.deadline - time.monotonic()
        if self.calls >= 40 or remaining <= 0:
            raise DiagnosticBudgetExceeded("Live diagnostic model budget reached")
        self.calls += 1
        kwargs["timeout_seconds"] = min(kwargs["timeout_seconds"], remaining)
        task = kwargs["request"].metadata.get("task_type", kwargs["request"].role.value)
        print(f"MODEL START {self.calls}/40 task={task}", flush=True)
        started = time.monotonic()
        try:
            response = super().generate_structured(**kwargs)
        except Exception as error:
            print(f"MODEL FAILED {self.calls} category={type(error).__name__}", flush=True)
            raise
        print(
            f"MODEL RETURNED {self.calls} seconds={time.monotonic() - started:.2f} "
            f"input_tokens={response.input_tokens} output_tokens={response.output_tokens}",
            flush=True,
        )
        return response


async def run(live):
    base = load_live_settings()
    if base.llm_provider != "nvidia":
        raise ValueError("Expected the current NVIDIA configuration")
    draft = sample_profile_draft()
    profile = build_candidate_profile(draft, approved=True)
    goal = CareerGoal(
        goal_type=GoalType.CURRENT_MARKET_ANALYSIS,
        target_role="Senior Java Developer",
        target_location="Toronto, Canada",
        geography_scopes=[GeographyScope.METRO_AREA],
        target_timeline_months=None,
        search_expansion_permission=True,
        approval_status=ApprovalStatus.APPROVED,
        approved_at=datetime.now(UTC),
    )
    print(
        f"Profile: {profile.current_role}; years={profile.years_professional_experience}; "
        f"explicit_evidence={len(profile.evidence_items)}",
        flush=True,
    )
    print(f"Goal: {goal.target_role}; Toronto metro; no fixed timeline", flush=True)
    print(f"Model: {base.extraction_model}; live={live}; output ceiling=20000", flush=True)
    if not live:
        return
    os.environ["LANGSMITH_TRACING"] = "false"
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    destination = Path("outputs/demo-profile-live") / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    destination.mkdir(parents=True, exist_ok=False)
    settings = base.model_copy(
        update={
            "model_timeout_seconds": 600,
            "max_retries": 0,
            "langsmith_tracing": False,
            "model_inspector_enabled": True,
            "run_audit_directory": destination / "run-audits",
        }
    )
    secrets = tuple(
        value.get_secret_value()
        for name in type(settings).model_fields
        if hasattr((value := getattr(settings, name)), "get_secret_value")
    )
    inspector = PersistedInspector(destination / "model-events.json", secrets=secrets)
    provider = BoundedProvider(settings.nvidia_api_key)
    gateway = DiagnosticGateway.from_settings(settings, providers={"nvidia": provider})
    gateway.output_token_limit = 20000
    gateway.inspector = inspector
    provider.inspector = inspector
    content_store = TransientMarketContentStore()
    context = WorkflowRuntimeContext(
        settings=settings,
        model_gateway=gateway,
        market_client_factory=lambda: build_enrichment_market_client(settings),
        structured_market_client_factory=lambda: build_primary_market_client(settings),
        content_store=content_store,
    )
    controller = CareerWorkflowController(build_career_graph(), context)
    run_id = uuid4()
    thread_id = f"demo-backend-{run_id}"
    report = {
        "mode": "LIVE_BACKEND_SYNTHETIC_DEMO",
        "run_id": str(run_id),
        "thread_id": thread_id,
        "started_at": datetime.now(UTC).isoformat(),
        "profile_draft": draft,
        "confirmed_profile": profile,
        "goal": goal,
        "scope": {
            "synthetic_base_inputs_confirmed_for_test": True,
            "inferred_strengths_auto_approved": False,
            "plan_auto_approved": False,
            "browser_session_changed": False,
            "max_output_tokens": 20000,
            "model_timeout_seconds": 600,
            "max_model_calls": 40,
            "model_deadline_seconds": 1800,
            "max_retries": 0,
            "market_analysis_posting_limit": settings.market_analysis_posting_limit,
            "market_max_total_search_calls": settings.market_max_total_search_calls,
            "market_max_content_fetches": settings.market_max_content_fetches,
        },
        "progress": [],
        "failure": None,
    }
    sanitizer = LocalModelInspector(secrets=secrets, max_events=1)

    def save():
        sanitizer.record("report", data=to_jsonable_python(report))
        (destination / "results.json").write_text(
            json.dumps(sanitizer.events[0]["data"], indent=2), encoding="utf-8"
        )

    save()
    started = time.monotonic()
    print(f"Artifacts: {destination.resolve()}", flush=True)
    try:
        inference = await asyncio.to_thread(infer_capabilities, profile, gateway)
        report["ai_strength_review"] = inference
        report["inference_handling"] = (
            "Suggestions retained for inspection only. Market/comparison uses explicit demo "
            "profile facts, without promoting unreviewed model suggestions."
        )
        print(f"STRENGTH REVIEW: {inference.status}", flush=True)
        save()
        async with asyncio.timeout(max(1, 1800 - (time.monotonic() - started))):
            async for node in controller.stream_start(
                thread_id=thread_id,
                confirmed_profile=profile,
                confirmed_goal=goal,
                capability_inference_requested=False,
                run_id=run_id,
            ):
                report["progress"].append(
                    {"node": node, "seconds": round(time.monotonic() - started, 2)}
                )
                report["graph_state"] = controller.inspect(thread_id=thread_id).state
                save()
                print(f"NODE COMPLETE: {node}", flush=True)
    except Exception as error:
        report["failure"] = {"category": type(error).__name__}
        print(f"WORKFLOW EXCEPTION: {type(error).__name__}", flush=True)
    finally:
        try:
            result = controller.inspect(thread_id=thread_id)
            state = result.state
            report["graph_state"] = state
            report["interrupts"] = result.interrupts
            report["market_view"] = market_view_model(state)
            report["analysis_view"] = analysis_view_model(state)
            if state.get("career_plan") is not None:
                report["plan_view"] = plan_view_model(
                    state["career_plan"],
                    state.get("role_assessment"),
                    state.get("career_assessment_synthesis"),
                )
        except Exception as error:
            report["view_or_state_export_error"] = type(error).__name__
        report["retained_posting_evidence"] = content_store.get_posting_evidence(run_id)
        report["finished_at"] = datetime.now(UTC).isoformat()
        report["elapsed_seconds"] = round(time.monotonic() - started, 2)
        report["actual_model_calls"] = provider.calls
        save()
        print(f"FINISHED: {destination.resolve() / 'results.json'}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.live))
