"""Explicit bounded live reproduction of the app's confirmed-demo-to-plan workflow."""

import argparse
import asyncio
import json
import os
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from check_demo_to_analysis import BoundedRecorder
from pydantic_core import to_jsonable_python

from ai_career_navigator.domain import CareerGoal
from ai_career_navigator.models.inspection import LocalModelInspector
from ai_career_navigator.models.providers import configured_provider
from ai_career_navigator.profile.service import build_candidate_profile
from ai_career_navigator.ui.demo_data import sample_profile_draft
from ai_career_navigator.ui.live_workflow import build_live_workflow_runtime, load_live_settings


async def run(target_role="Senior Java developer", goal_type="CURRENT_MARKET_ANALYSIS"):
    os.environ["LANGSMITH_TRACING"] = "false"
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    output = Path("outputs/live-failure-check") / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output.mkdir(parents=True)
    settings = load_live_settings().model_copy(
        update={
            "langsmith_tracing": False,
            "run_audit_directory": output / "run-audits",
        }
    )
    secrets = tuple(
        v.get_secret_value()
        for n in type(settings).model_fields
        if hasattr((v := getattr(settings, n)), "get_secret_value")
    )
    sanitizer = LocalModelInspector(secrets=secrets, max_events=1)
    recorder = BoundedRecorder(configured_provider(settings), output, sanitizer, max_calls=4)
    recorder.deadline = time.monotonic() + 900
    runtime = build_live_workflow_runtime(settings, provider_override=recorder)
    profile = build_candidate_profile(sample_profile_draft(), approved=True)
    goal = CareerGoal(
        goal_type=goal_type,
        target_role=target_role,
        target_location="Toronto, Canada",
        geography_scopes=["METRO_AREA"],
        search_expansion_permission=True,
        approval_status="APPROVED",
        approved_at=datetime.now(UTC),
    )
    run_id = uuid4()
    thread = f"diagnostic-{run_id}"
    report = {"mode": "LIVE_PROVIDERS_SYNTHETIC_DEMO", "steps": [], "run_id": str(run_id)}
    start = previous = time.monotonic()
    print(f"OUTPUT {output.resolve()}", flush=True)
    print(
        f"MARKET timeout={settings.market_timeout_seconds}s "
        f"provider={settings.market_primary_provider}",
        flush=True,
    )

    def save():
        report["seconds"] = round(time.monotonic() - start, 2)
        report["model_calls"] = recorder.calls
        sanitizer.record("report", data=to_jsonable_python(report))
        (output / "results.json").write_text(
            json.dumps(sanitizer.events[-1]["data"], indent=2), encoding="utf-8"
        )

    try:
        async with asyncio.timeout(900):
            async for node in runtime.controller.stream_start(
                thread_id=thread,
                confirmed_profile=profile,
                confirmed_goal=goal,
                capability_inference_requested=False,
                run_id=run_id,
            ):
                now = time.monotonic()
                report["steps"].append({"stage": node, "seconds": round(now - previous, 2)})
                previous = now
                report["state"] = runtime.controller.inspect(thread_id=thread).state
                save()
                print(f"STEP {node} {report['steps'][-1]['seconds']}s", flush=True)
    except Exception as exc:
        report["exception"] = type(exc).__name__
        # Locations only, never exception messages/locals containing response data or secrets.
        report["frames"] = [
            {"file": Path(f.filename).name, "line": f.lineno, "function": f.name}
            for f in traceback.extract_tb(exc.__traceback__)
        ]
        if hasattr(exc, "errors"):
            report["validation"] = [
                {"loc": e["loc"], "type": e["type"]} for e in exc.errors(include_input=False)
            ]
    finally:
        report["state"] = runtime.controller.inspect(thread_id=thread).state
        report["posting_evidence"] = runtime.controller._context.content_store.get_posting_evidence(
            run_id
        )
        save()
        state = report["state"]
        assessment = state.get("same_role_assessment") or state.get("transition_assessment")
        print(
            json.dumps(
                {
                    "seconds": report["seconds"],
                    "exception": report.get("exception"),
                    "frames": report.get("frames"),
                    "validation": report.get("validation"),
                    "last_error": state.get("last_error"),
                    "status": state.get("workflow_status"),
                    "postings": len(report["posting_evidence"]),
                    "model_calls": recorder.calls,
                    "assessment": bool(assessment),
                    "plan": bool(state.get("career_plan")),
                    "processing_issues": getattr(assessment, "processing_issues", []),
                },
                default=str,
            ),
            flush=True,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True)
    parser.add_argument("--target-role", default="Senior Java developer")
    parser.add_argument(
        "--goal-type",
        default="CURRENT_MARKET_ANALYSIS",
        choices=["CURRENT_MARKET_ANALYSIS", "ROLE_TRANSITION", "TARGET_CAREER_PATH"],
    )
    args = parser.parse_args()
    asyncio.run(run(args.target_role, args.goal_type))
