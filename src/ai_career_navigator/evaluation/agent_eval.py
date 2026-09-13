"""Routing accuracy and task-completion-rate aggregation for the LangGraph workflow.

The conditional-edge functions in `ai_career_navigator.orchestration.routing` are
pure functions of `CareerGraphState`, so routing accuracy can be checked without
running the graph: construct a state for a scenario, call the router, and compare
its decision to what a correct workflow should do next. Task completion rate is
the same idea one level up -- did a scripted end-to-end scenario (driven through
`CareerWorkflowController`, e.g. via the fakes in `tests/orchestration/conftest.py`)
land on the `WorkflowStatus` it was designed to reach.

Building the states/scenarios needs real domain objects (RoleAssessment, GapItem,
a running controller), so that construction stays in the test suite; this module
only owns the aggregation math, matching how `evaluation.runner` separates
grading a single case from summarizing a run.
"""

from pydantic import BaseModel, ConfigDict, Field


class RoutingCaseResult(BaseModel):
    """One routing decision checked against the scripted-correct next node."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    router_name: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    expected_route: str = Field(min_length=1)
    actual_route: str = Field(min_length=1)

    @property
    def correct(self) -> bool:
        return self.actual_route == self.expected_route


class RoutingAccuracySummary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    total_cases: int = Field(ge=0)
    correct_cases: int = Field(ge=0)
    accuracy: float = Field(ge=0.0, le=1.0)
    per_router_accuracy: dict[str, float]


def summarize_routing_accuracy(results: list[RoutingCaseResult]) -> RoutingAccuracySummary:
    by_router: dict[str, list[RoutingCaseResult]] = {}
    for result in results:
        by_router.setdefault(result.router_name, []).append(result)
    correct = sum(result.correct for result in results)
    return RoutingAccuracySummary(
        total_cases=len(results),
        correct_cases=correct,
        accuracy=(correct / len(results) if results else 0.0),
        per_router_accuracy={
            router: sum(item.correct for item in items) / len(items)
            for router, items in sorted(by_router.items())
        },
    )


class WorkflowScenarioResult(BaseModel):
    """One scripted end-to-end scenario checked against its expected terminal status."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    scenario_id: str = Field(min_length=1)
    expected_status: str = Field(min_length=1)
    actual_status: str = Field(min_length=1)

    @property
    def completed_as_expected(self) -> bool:
        return self.actual_status == self.expected_status


class TaskCompletionSummary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    total_scenarios: int = Field(ge=0)
    completed_scenarios: int = Field(ge=0)
    completion_rate: float = Field(ge=0.0, le=1.0)


def summarize_task_completion(results: list[WorkflowScenarioResult]) -> TaskCompletionSummary:
    completed = sum(result.completed_as_expected for result in results)
    return TaskCompletionSummary(
        total_scenarios=len(results),
        completed_scenarios=completed,
        completion_rate=(completed / len(results) if results else 0.0),
    )
