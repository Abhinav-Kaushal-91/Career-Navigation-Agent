"""Run reviewed Career Navigator pilot cases through the unchanged live workflow."""

import argparse
import asyncio
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import requests
from dotenv import dotenv_values
from langsmith import Client, trace

from ai_career_navigator.config import Settings
from ai_career_navigator.evaluation.pilot import (
    build_workflow_inputs,
    execution_payload,
    load_pilot_cases,
    map_accessibility_to_verdict,
)
from ai_career_navigator.ui.live_workflow import build_live_workflow_runtime


def _value(value):  # type: ignore[no-untyped-def]
    return getattr(value, "value", value)


async def _run(args: argparse.Namespace) -> None:
    settings = Settings(_env_file=args.env_file)
    env_values = dotenv_values(args.env_file)
    if not all(
        (settings.langsmith_api_key, settings.langsmith_project, settings.langsmith_workspace_id)
    ):
        raise ValueError("LangSmith API key, project, and workspace ID are required")
    client = Client(
        api_key=env_values["LANGSMITH_API_KEY"],
        api_url=env_values["LANGSMITH_ENDPOINT"],
    )
    cases = load_pilot_cases(args.workbook)
    if args.case_id:
        requested = set(args.case_id)
        cases = [case for case in cases if case.execution.case_id in requested]
        if not cases:
            raise ValueError(f"unknown case IDs: {sorted(requested)}")
    output = []
    for case in cases:
        runtime = build_live_workflow_runtime(settings)
        profile, goal = build_workflow_inputs(case)
        experiment_slug = args.experiment_name.casefold().replace(" ", "-")
        thread_id = f"{experiment_slug}-{case.execution.case_id.lower()}"
        started = time.perf_counter()
        trace_started = datetime.now(UTC)
        persisted_trace_id = str(uuid4())
        state = {}
        completed_nodes = []
        with trace(
            f"{args.experiment_name} {case.execution.case_id}",
            inputs=execution_payload(case),
            project_name=settings.langsmith_project,
            client=client,
            tags=["career-navigator", experiment_slug, case.execution.case_id],
            metadata={"adapter_version": args.adapter_version, "target_location": "Canada"},
        ) as root:
            try:
                async for node in runtime.controller.stream_start(
                    thread_id=thread_id,
                    confirmed_profile=profile,
                    confirmed_goal=goal,
                    capability_inference_requested=False,
                ):
                    completed_nodes.append(node)
                state = runtime.controller.inspect(thread_id=thread_id).state
                assessment = state.get("role_assessment")
                synthesis = state.get("career_assessment_synthesis")
                if assessment is None:
                    raise RuntimeError("workflow produced no role assessment")
                verdict = map_accessibility_to_verdict(assessment.candidate_accessibility)
                result = {
                    "case_id": case.execution.case_id,
                    "expected_career_verdict": case.reference.expected_career_verdict,
                    "predicted_career_verdict": verdict,
                    "verdict_exact_match": int(verdict == case.reference.expected_career_verdict),
                    "actual_strengths": [
                        x.title for x in getattr(synthesis, "demonstrated_strengths", [])
                    ],
                    "actual_gaps": [
                        x.display_title for x in getattr(synthesis, "grouped_gaps", [])
                    ],
                    "actual_match_types": [
                        _value(x.match_type) for x in assessment.requirement_comparisons
                    ],
                    "actual_gap_severity": [_value(x.severity) for x in assessment.gaps],
                    "latency_seconds": round(time.perf_counter() - started, 3),
                    "token_usage": runtime.model_usage.input_tokens
                    + runtime.model_usage.output_tokens,
                    "input_tokens": runtime.model_usage.input_tokens,
                    "output_tokens": runtime.model_usage.output_tokens,
                    "cost": None,
                    "langsmith_trace_id": persisted_trace_id,
                    "workflow_status": _value(state.get("workflow_status")),
                    "completed_nodes": completed_nodes,
                    "error": None,
                }
                root.end(
                    outputs={k: v for k, v in result.items() if k != "expected_career_verdict"}
                )
            except Exception as error:
                workflow_status = _value(state.get("workflow_status"))
                terminal_verdict = (
                    "insufficient_evidence"
                    if workflow_status == "INSUFFICIENT_EVIDENCE"
                    else None
                )
                result = {
                    "case_id": case.execution.case_id,
                    "expected_career_verdict": case.reference.expected_career_verdict,
                    "predicted_career_verdict": terminal_verdict,
                    "verdict_exact_match": 0,
                    "latency_seconds": round(time.perf_counter() - started, 3),
                    "token_usage": runtime.model_usage.input_tokens
                    + runtime.model_usage.output_tokens,
                    "cost": None,
                    "langsmith_trace_id": persisted_trace_id,
                    "workflow_status": workflow_status,
                    "completed_nodes": completed_nodes,
                    "last_error": state.get("last_error"),
                    "limitations": state.get("limitations", []),
                    "error": f"{type(error).__name__}: {error}",
                }
                root.end(error=result["error"])
            output.append(result)
            print(json.dumps(result))
        client.flush()
        response = requests.post(
            f"{env_values['LANGSMITH_ENDPOINT']}/runs",
            headers={
                "X-API-Key": env_values["LANGSMITH_API_KEY"],
            },
            json={
                "id": result["langsmith_trace_id"],
                "name": f"{args.experiment_name} {case.execution.case_id}",
                "run_type": "chain",
                "inputs": execution_payload(case),
                "outputs": {
                    key: value for key, value in result.items() if key != "expected_career_verdict"
                },
                "error": result.get("error"),
                "start_time": trace_started.isoformat(),
                "end_time": datetime.now(UTC).isoformat(),
                "session_name": settings.langsmith_project,
                "extra": {"metadata": {"adapter_version": args.adapter_version}},
            },
            timeout=30,
        )
        response.raise_for_status()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(output, indent=2), encoding="utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workbook", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--case-id", action="append")
    parser.add_argument("--experiment-name", default="Baseline V1")
    parser.add_argument("--adapter-version", default="pilot-v1.1")
    asyncio.run(_run(parser.parse_args()))


if __name__ == "__main__":
    main()
