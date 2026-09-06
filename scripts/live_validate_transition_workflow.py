"""Run a bounded, sanitized live career-transition workflow diagnostic."""

import argparse
import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from ai_career_navigator.domain import ApprovalStatus, CareerGoal, GeographyScope, GoalType
from ai_career_navigator.ui.demo_data import CANDIDATE_PROFILE
from ai_career_navigator.ui.live_workflow import (
    build_live_workflow_runtime,
    load_live_settings,
)


async def _run() -> None:
    runtime = build_live_workflow_runtime(load_live_settings())
    goal = CareerGoal(
        goal_type=GoalType.ROLE_TRANSITION,
        target_role="AI Solutions Architect",
        target_timeline_months=24,
        target_location="Canada",
        preferred_work_modes=["Hybrid", "Remote"],
        geography_scopes=[GeographyScope.COUNTRY],
        bridge_role_willingness=True,
        search_expansion_permission=True,
        approval_status=ApprovalStatus.APPROVED,
        approved_at=datetime.now(UTC),
    )
    thread_id = f"transition-diagnostic-{uuid4()}"
    try:
        async for node in runtime.controller.stream_start(
            thread_id=thread_id,
            confirmed_profile=CANDIDATE_PROFILE,
            confirmed_goal=goal,
            capability_inference_requested=False,
        ):
            print(f"completed_node={node}")
    except Exception as error:
        print(f"exception_category={type(error).__name__}")
        try:
            recovered = runtime.controller.inspect(thread_id=thread_id)
        except Exception as inspect_error:
            print(f"inspect_exception_category={type(inspect_error).__name__}")
        else:
            state = recovered.state
            print(f"recovered_stage={state.get('current_stage')}")
            print(f"recovered_status={state.get('workflow_status')}")
            print(f"recovered_last_error={state.get('last_error')}")
        raise

    result = runtime.controller.inspect(thread_id=thread_id)
    state = result.state
    print(f"final_stage={state.get('current_stage')}")
    print(f"final_status={state.get('workflow_status')}")
    print(f"last_error={state.get('last_error')}")
    validated = getattr(state.get("market_snapshot"), "validated_posting_count", 0)
    analyzed = getattr(state.get("requirement_summary"), "analyzed_posting_count", 0)
    print(f"validated_postings={validated}")
    print(f"analyzed_postings={analyzed}")
    print(f"nvidia_calls={runtime.model_usage.calls}")
    print(f"nvidia_failed_calls={runtime.model_usage.failed_calls}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    asyncio.run(_run())


if __name__ == "__main__":
    main()
