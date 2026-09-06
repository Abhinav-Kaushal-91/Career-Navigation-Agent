"""Deterministic navigation rules for structured profile onboarding."""

from dataclasses import dataclass

PROFILE_ONBOARDING_STEPS = (
    "About You",
    "Professional Profile",
    "Portfolio Projects",
    "Education",
    "AI Strength Identification",
    "Review",
)


@dataclass(frozen=True)
class ProfileStepState:
    label: str
    number: int
    status: str
    available: bool


def profile_step_index(step: str) -> int:
    if step not in PROFILE_ONBOARDING_STEPS:
        raise ValueError(f"unknown profile onboarding step: {step}")
    return PROFILE_ONBOARDING_STEPS.index(step)


def next_profile_highest(highest: str, destination: str) -> str:
    return destination if profile_step_index(destination) > profile_step_index(highest) else highest


def can_navigate_profile_step(destination: str, highest: str) -> bool:
    return profile_step_index(destination) <= profile_step_index(highest)


def profile_step_states(current: str, highest: str) -> tuple[ProfileStepState, ...]:
    current_index = profile_step_index(current)
    highest_index = profile_step_index(highest)
    return tuple(
        ProfileStepState(
            label=step,
            number=index + 1,
            status=(
                "current"
                if index == current_index
                else "complete"
                if index < current_index
                else "available"
                if index <= highest_index
                else "upcoming"
            ),
            available=index <= highest_index,
        )
        for index, step in enumerate(PROFILE_ONBOARDING_STEPS)
    )
