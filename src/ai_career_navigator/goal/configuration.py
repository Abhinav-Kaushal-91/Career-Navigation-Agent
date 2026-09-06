"""Intent-specific field policy for V1 career-goal capture."""

from dataclasses import dataclass

from ai_career_navigator.domain import GoalType


@dataclass(frozen=True)
class GoalIntentConfig:
    label: str
    description: str
    requires_target: bool = False
    target_label: str | None = None
    show_timeline: bool = False
    show_bridge_willingness: bool = False
    show_search_expansion: bool = False


GOAL_INTENT_CONFIGS = {
    GoalType.CURRENT_MARKET_ANALYSIS: GoalIntentConfig(
        label="Find roles I can target now",
        description=(
            "Explore a role you could target now. A role title is optional while saving "
            "the goal, but is required to run the current V1 market analysis."
        ),
        target_label="Role to assess now (optional)",
    ),
    GoalType.ROLE_TRANSITION: GoalIntentConfig(
        label="Explore a career transition",
        description="Examine a transition into a specific role without assuming it is feasible.",
        requires_target=True,
        target_label="Role you want to transition into",
        show_timeline=True,
        show_bridge_willingness=True,
        show_search_expansion=True,
    ),
    GoalType.TARGET_CAREER_PATH: GoalIntentConfig(
        label="Plan toward a target role",
        description="Capture a specific destination and the path preferences you want assessed.",
        requires_target=True,
        target_label="Target role",
        show_timeline=True,
        show_bridge_willingness=True,
        show_search_expansion=True,
    ),
    GoalType.LEADERSHIP_PROGRESSION: GoalIntentConfig(
        label="Explore leadership progression",
        description="Explore leadership scope, with an optional destination role or level.",
        target_label="Leadership role or level (optional)",
        show_timeline=True,
        show_search_expansion=True,
    ),
    GoalType.CAREER_EXPLORATION: GoalIntentConfig(
        label="I’m not sure yet",
        description="Explore plausible directions without forcing a target role or timeline.",
    ),
    GoalType.CAREER_REASSESSMENT: GoalIntentConfig(
        label="Reassess an existing direction",
        description=(
            "Revisit a known direction or changed preferences without historical comparison."
        ),
        target_label="Current target role (optional)",
        show_timeline=True,
        show_bridge_willingness=True,
        show_search_expansion=True,
    ),
}


def goal_intent_config(goal_type: GoalType) -> GoalIntentConfig:
    try:
        return GOAL_INTENT_CONFIGS[goal_type]
    except KeyError as error:
        raise ValueError(f"unsupported goal type: {goal_type}") from error


def goal_type_label(goal_type: GoalType) -> str:
    return goal_intent_config(goal_type).label
