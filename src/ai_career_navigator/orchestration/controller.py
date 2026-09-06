"""Thin application-facing controller for starting, resuming, and inspecting runs."""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import UUID, uuid4

from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from ai_career_navigator.domain import CandidateProfile, CareerGoal

from .approval import PlanReviewAction, PlanReviewRequest
from .context import WorkflowRuntimeContext
from .state import CareerGraphState, HumanAction


@dataclass(frozen=True)
class WorkflowResult:
    state: CareerGraphState
    interrupts: tuple[dict[str, object], ...] = ()

    @property
    def interrupted(self) -> bool:
        return bool(self.interrupts)


class CareerWorkflowController:
    """Keep callers independent of raw LangGraph invocation details."""

    def __init__(self, graph: CompiledStateGraph, context: WorkflowRuntimeContext) -> None:
        self._graph = graph
        self._context = context

    @staticmethod
    def _config(thread_id: str) -> dict[str, dict[str, str]]:
        if not thread_id.strip():
            raise ValueError("thread_id must not be blank")
        return {"configurable": {"thread_id": thread_id}}

    @staticmethod
    def _result(raw: dict[str, object]) -> WorkflowResult:
        interrupts = tuple(
            item.value for item in raw.get("__interrupt__", ()) if isinstance(item.value, dict)
        )
        state = {key: value for key, value in raw.items() if key != "__interrupt__"}
        return WorkflowResult(state=state, interrupts=interrupts)  # type: ignore[arg-type]

    @staticmethod
    def _initial_state(
        *,
        thread_id: str,
        confirmed_profile: CandidateProfile | None,
        confirmed_goal: CareerGoal | None,
        capability_inference_requested: bool,
        run_id: UUID | None,
    ) -> dict[str, object]:
        return {
            "run_id": run_id or uuid4(),
            "thread_id": thread_id,
            "confirmed_profile": confirmed_profile,
            "confirmed_goal": confirmed_goal,
            "capability_inference_requested": capability_inference_requested,
        }

    async def start(
        self,
        *,
        thread_id: str,
        confirmed_profile: CandidateProfile | None = None,
        confirmed_goal: CareerGoal | None = None,
        capability_inference_requested: bool = True,
        run_id: UUID | None = None,
    ) -> WorkflowResult:
        initial = self._initial_state(
            thread_id=thread_id,
            confirmed_profile=confirmed_profile,
            confirmed_goal=confirmed_goal,
            capability_inference_requested=capability_inference_requested,
            run_id=run_id,
        )
        raw = await self._graph.ainvoke(
            initial,
            config=self._config(thread_id),
            context=self._context,
        )
        return self._result(raw)

    async def stream_start(
        self,
        *,
        thread_id: str,
        confirmed_profile: CandidateProfile | None = None,
        confirmed_goal: CareerGoal | None = None,
        capability_inference_requested: bool = True,
        run_id: UUID | None = None,
    ) -> AsyncIterator[str]:
        """Yield completed graph nodes so UI progress reflects actual execution."""

        initial = self._initial_state(
            thread_id=thread_id,
            confirmed_profile=confirmed_profile,
            confirmed_goal=confirmed_goal,
            capability_inference_requested=capability_inference_requested,
            run_id=run_id,
        )
        async for update in self._graph.astream(
            initial,
            config=self._config(thread_id),
            context=self._context,
            stream_mode="updates",
        ):
            if not isinstance(update, dict):
                continue
            for node_name in update:
                if node_name != "__interrupt__":
                    yield node_name

    async def resume_inference_review(
        self,
        *,
        thread_id: str,
        reviewed_profile: CandidateProfile,
    ) -> WorkflowResult:
        raw = await self._graph.ainvoke(
            Command(
                resume={
                    "confirmed_profile": reviewed_profile.model_dump(mode="json"),
                    "review_completed": True,
                }
            ),
            config=self._config(thread_id),
            context=self._context,
        )
        return self._result(raw)

    async def submit_plan_action(
        self,
        *,
        thread_id: str,
        plan_id: UUID,
        plan_version: int,
        action: PlanReviewAction,
    ) -> WorkflowResult:
        """Resume final review only for the exact checkpointed plan version."""

        request = PlanReviewRequest(
            plan_id=plan_id,
            plan_version=plan_version,
            action=action,
        )
        current = self.inspect(thread_id=thread_id)
        records = current.state.get("workflow_action_records", [])
        if records:
            previous = records[-1]
            if (
                previous.plan_id == request.plan_id
                and previous.plan_version == request.plan_version
                and previous.action is request.action
            ):
                return current
            raise ValueError("a different final plan action has already been recorded")
        plan = current.state.get("career_plan")
        if plan is None:
            raise ValueError("no career plan is available for final review")
        if plan.plan_id != request.plan_id or plan.plan_version != request.plan_version:
            raise ValueError("plan review request does not match the checkpointed plan version")
        if (
            not current.interrupted
            or current.state.get("human_action_required") is not HumanAction.FINAL_PLAN_REVIEW
        ):
            raise ValueError("workflow is not waiting for final plan review")
        raw = await self._graph.ainvoke(
            Command(resume=request.model_dump(mode="json")),
            config=self._config(thread_id),
            context=self._context,
        )
        return self._result(raw)

    def inspect(self, *, thread_id: str) -> WorkflowResult:
        snapshot = self._graph.get_state(self._config(thread_id))
        interrupts = tuple(
            item.value
            for task in snapshot.tasks
            for item in task.interrupts
            if isinstance(item.value, dict)
        )
        return WorkflowResult(state=snapshot.values, interrupts=interrupts)
