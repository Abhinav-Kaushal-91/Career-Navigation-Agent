"""Goal-specific orientation, not a readiness policy or recommendation."""

from ai_career_navigator.domain import GoalType

DIRECTION_COPY = {
    GoalType.CURRENT_MARKET_ANALYSIS: "Find roles you can target now",
    GoalType.ROLE_TRANSITION: "Explore a career transition",
    GoalType.TARGET_CAREER_PATH: "Plan toward your target role",
    GoalType.LEADERSHIP_PROGRESSION: "Explore leadership progression",
    GoalType.CAREER_EXPLORATION: "Explore possible career directions",
    GoalType.CAREER_REASSESSMENT: "Reassess your career direction",
}


def direction_caption(goal):
    return DIRECTION_COPY.get(getattr(goal, "goal_type", None), "")


def position_label(value):
    return {
        "Yes": "Demonstrated", "No": "Needs development", "Unknown": "Unconfirmed",
        "Partial": "Partially demonstrated", "Transferable": "Transferable",
    }.get(value, value)
