"""Career roadmap timeline presentation."""

from collections.abc import Sequence

from ai_career_navigator.domain import PlanMilestone


def group_milestones(milestones: Sequence[PlanMilestone]) -> dict[str, tuple[PlanMilestone, ...]]:
    """Group ordered synthetic milestones by their phase label."""

    grouped: dict[str, list[PlanMilestone]] = {}
    for milestone in milestones:
        grouped.setdefault(milestone.phase, []).append(milestone)
    return {phase: tuple(items) for phase, items in grouped.items()}
